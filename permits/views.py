import csv
import datetime
from datetime import timedelta
from decimal import Decimal
import io
import json
import logging
import mimetypes
import os
import zipfile

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseNotAllowed, FileResponse, Http404, StreamingHttpResponse
from django.core.exceptions import PermissionDenied, ValidationError, ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.core import signing
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.sessions.models import Session

from .models import (
    CustomUser, Barangay, Category, Record, Document,
    AuditLog, LoginAttempt, PasswordHistory,
    EngineeringRecord, PermitDetail, ProjectDetail,
    RequirementTemplate, RequirementItem, RecordRequirement,
    BlockedIP,
)
from .validators import validate_document_file, sanitize_input, validate_password_strength
from .utils import get_client_ip
from .permissions import role_required, admin_required, staff_or_admin_required, has_role
from .services import (
    get_office_settings, save_office_settings,
    build_record_zip_buffer, build_category_zip_buffer, build_barangay_zip_buffer,
    sanitize_zip_name, sanitize_file_name,
    send_document_expiry_alerts, build_activity_logs_csv_rows, filter_engineering_records,
    parse_decimal_safely
)


from .forms import UserCreationForm, UserEditForm, FlagIllegalConstructionForm, OfficeSettingsForm

logger = logging.getLogger('permits')


def log_audit(user, action, target_record_id=None, request=None):
    # Prevent logging repetitive routine activities to keep AuditLogs clean and readable
    ignored_actions = [
        "Logged out",
        "Logged in successfully",
        "Logged in successfully from a new IP/device"
    ]
    if action in ignored_actions:
        return
        
    ip = get_client_ip(request) if request else None
    AuditLog.objects.create(
        user=user,
        action=action,
        target_record_id=target_record_id,
        ip_address=ip
    )


def check_lockout(email, ip_address):
    fifteen_mins_ago = timezone.now() - timedelta(minutes=15)
    total_failures = LoginAttempt.objects.filter(email_attempted=email, success=False).count()
    if total_failures >= 10:
        User = get_user_model()
        user_obj = User.objects.filter(email=email).first()
        if user_obj and user_obj.is_active:
            user_obj.is_active = False
            user_obj.save()
            log_audit(user_obj, "Account locked out permanently (10 failed attempts)", request=None)
        return True, "Account locked. Please contact the administrator for unlock."

    recent_failures = LoginAttempt.objects.filter(
        email_attempted=email,
        success=False,
        timestamp__gte=fifteen_mins_ago
    ).order_by('-timestamp')

    if recent_failures.count() >= 5:
        fifth_failure = recent_failures[4]
        elapsed = timezone.now() - fifth_failure.timestamp
        remaining = 15 - int(elapsed.total_seconds() / 60)
        if remaining > 0:
            return True, f"Account temporarily locked. Try again in {remaining} minutes."

    return False, None




def get_per_page(request, default=10):
    val = request.GET.get('per_page', '')
    try:
        val = int(val)
        if val in [10, 20, 50, 100]:
            return val
    except ValueError:
        pass
    return default


def get_year_choices():
    from django.core.cache import cache
    cached = cache.get('year_choices_list')
    if cached is not None:
        return cached
    db_years = set(EngineeringRecord.objects.exclude(year__isnull=True).values_list('year', flat=True))
    from datetime import date
    current_year = date.today().year
    default_years = set(range(current_year + 1, current_year - 15, -1))
    all_years = sorted(list(db_years.union(default_years)), reverse=True)
    cache.set('year_choices_list', all_years, timeout=300)
    return all_years


def resolve_scope(request):
    """
    Resolves record filtering scope ('my' vs 'all') based on 'scope' GET parameter.
    If scope is not explicitly passed:
    - Admin / Municipal Engineer: default to 'all'
    - Engineering Staff: default to 'my'
    """
    scope = request.GET.get('scope', '').strip().lower()
    if scope not in ['my', 'all']:
        if hasattr(request, 'user') and request.user.is_authenticated and getattr(request.user, 'role', '') == 'staff':
            scope = 'my'
        else:
            scope = 'all'
    return scope


# ─── PUBLIC LANDING ─────────────────────────────────────────────────────────


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


# ─── AUTHENTICATION ──────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        ip_address = get_client_ip(request)

        is_locked, lockout_msg = check_lockout(email, ip_address)
        if is_locked:
            messages.error(request, lockout_msg)
            return render(request, 'permits/login.html')

        User = get_user_model()
        user_obj = User.objects.filter(email=email).first()
        username = user_obj.username if user_obj else None

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                LoginAttempt.objects.create(email_attempted=email, success=False, ip_address=ip_address)
                messages.error(request, "Account is locked. Please contact the administrator.")
                return render(request, 'permits/login.html')

            if user.session_key:
                try:
                    Session.objects.filter(session_key=user.session_key).delete()
                except Exception as e:
                    logger.error(f"Error terminating previous session: {e}")

            LoginAttempt.objects.create(email_attempted=email, success=True, ip_address=ip_address)
            login(request, user)

            # Handle Remember Me checkbox (Standard Security Best Practice)
            remember_me = request.POST.get('remember_me')
            if remember_me:
                # 14 days (2 weeks) industry standard session persistence
                request.session.set_expiry(1209600)
            else:
                # Expire session on browser close if unchecked
                request.session.set_expiry(0)

            user.session_key = request.session.session_key
            user.save()

            # Check if this is a login from a new IP/device
            has_previous_login = AuditLog.objects.filter(
                user=user,
                action__icontains="Logged in",
                ip_address=ip_address
            ).exists()
            
            action_text = "Logged in successfully"
            if ip_address and not has_previous_login:
                action_text = "Logged in successfully from a new IP/device"

            log_audit(user, action_text, request=request)
            return redirect('dashboard')
        else:
            LoginAttempt.objects.create(email_attempted=email, success=False, ip_address=ip_address)
            if user_obj:
                log_audit(user_obj, "Failed login attempt", request=request)
            messages.error(request, "Incorrect email or password.")

    return render(request, 'permits/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        log_audit(request.user, "Logged out", request=request)
        request.user.session_key = None
        request.user.save()
    logout(request)
    return redirect('login')


def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, "Please enter your registered email address.")
            return render(request, 'permits/forgot_password.html')

        User = get_user_model()
        user = User.objects.filter(email=email).first()

        # Check if user exists in database
        if not user:
            messages.error(request, f"No account found with email '{email}'. Please check your spelling or contact your administrator.")
            return render(request, 'permits/forgot_password.html')

        # User exists: generate secure signed token (valid for 30 minutes)
        try:
            token_data = {
                'user_id': user.pk,
                'email': user.email,
            }
            token = signing.dumps(token_data, salt='password-reset')

            # Build reset URL
            reset_url = request.build_absolute_uri(
                reverse('reset_password') + f'?token={token}'
            )

            # Send email via Django's configured email backend (Resend / Gmail SMTP / Console)
            from django.core.mail import send_mail
            from django.conf import settings
            from django.template.loader import render_to_string

            subject = 'eTala — Password Reset Request'
            user_display_name = user.full_name or user.username
            html_message = render_to_string('emails/email_password_reset.html', {
                'user_display_name': user_display_name,
                'reset_url': reset_url,
            })
            plain_message = f'Reset your eTala password: {reset_url}\nThis link is valid for 1 hour.'

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            log_audit(user, "Password reset email sent", request=request)
            logger.info(f"Password reset email sent to {email}")
            messages.success(request, f"Password reset link successfully sent to {email}. Please check your inbox!")
            return redirect('login')
        except Exception as exc:
            logger.error(f"Failed to send password reset email to {email}: {exc}")
            messages.error(request, f"Unable to send reset email at this moment: {exc}. Please try again later.")
            return render(request, 'permits/forgot_password.html')

    return render(request, 'permits/forgot_password.html')


def reset_password_view(request):
    """Handle the password reset link — validate token and allow new password."""
    token = request.GET.get('token') or request.POST.get('token', '')

    # Validate token (valid for 1 hour matching PASSWORD_RESET_TIMEOUT)
    reset_timeout = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
    try:
        token_data = signing.loads(token, salt='password-reset', max_age=reset_timeout)  # 30 min
    except signing.SignatureExpired:
        messages.error(request, "This password reset link has expired. Please request a new one.")
        return redirect('forgot_password')
    except signing.BadSignature:
        messages.error(request, "Invalid password reset link.")
        return redirect('forgot_password')

    User = get_user_model()
    user = User.objects.filter(pk=token_data['user_id'], email=token_data['email']).first()
    if not user:
        messages.error(request, "Invalid password reset link.")
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password or len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'permits/reset_password.html', {'token': token})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'permits/reset_password.html', {'token': token})

        # Check password history (prevent reuse of last 5 passwords)
        recent_passwords = PasswordHistory.objects.filter(user=user).order_by('-created_at')[:5]
        for ph in recent_passwords:
            if check_password(new_password, ph.password_hash):
                messages.error(request, "You cannot reuse your last 5 passwords.")
                return render(request, 'permits/reset_password.html', {'token': token})

        # Set the new password
        user.set_password(new_password)
        user.save()

        # Save to password history
        PasswordHistory.objects.create(user=user, password_hash=make_password(new_password))

        log_audit(user, "Password reset successfully via email link", request=request)
        messages.success(request, "Your password has been reset successfully. You can now log in.")
        return redirect('login')

    return render(request, 'permits/reset_password.html', {'token': token})



def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name = sanitize_input(request.POST.get('full_name', '')).strip()
        email = sanitize_input(request.POST.get('email', '')).strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        government_id = request.FILES.get('government_id')

        if not full_name or not email or not password or not confirm_password or not government_id:
            messages.error(request, "All required fields must be filled, including your Government ID.")
            return render(request, 'permits/register.html')

        try:
            validate_document_file(government_id)
        except ValidationError as ve:
            messages.error(request, f"Government ID upload invalid: {ve.message}")
            return render(request, 'permits/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'permits/register.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'permits/register.html')

        username = email.split('@')[0]
        base_username = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        ok, err_msg = validate_password_strength(password)
        if not ok:
            messages.error(request, err_msg)
            return render(request, 'permits/register.html')

        User = get_user_model()
        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role='staff'
        )
        new_user.save()

        log_audit(new_user, "Registered account", request=request)
        messages.success(request, "Account created successfully! Please sign in.")
        return redirect('login')

    return render(request, 'permits/register.html')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    records = EngineeringRecord.objects.exclude(status='archived')

    # Summary stats
    total_permits = records.filter(record_type='Permit').count()
    total_municipal = records.filter(record_type='Project', project_scope='Municipal').count()
    total_barangay = records.filter(record_type='Project', project_scope='Barangay').count()
    total_documents = Document.objects.filter(engineering_record__isnull=False).count()
    total_archived = EngineeringRecord.objects.filter(status='archived').count()
    total_records = records.count()

    # Incomplete records (have a checklist but not fully fulfilled or waived)
    incomplete_records = records.filter(
        requirements__isnull=False,
        requirements__is_fulfilled=False,
        requirements__is_waived=False
    ).distinct().count()

    # Checklist Digitization Compliance Stats
    active_with_reqs = records.annotate(
        total_reqs=Count('requirements'),
        fulfilled_reqs=Count('requirements', filter=Q(requirements__is_fulfilled=True) | Q(requirements__is_waived=True))
    ).filter(total_reqs__gt=0)
    
    compliance_total = active_with_reqs.count()
    compliance_completed = active_with_reqs.filter(total_reqs=F('fulfilled_reqs')).count()
    compliance_incomplete = compliance_total - compliance_completed
    compliance_rate = int((compliance_completed / compliance_total) * 100) if compliance_total > 0 else 100

    # Scope resolution & Recent records
    selected_scope = resolve_scope(request)
    my_records_count = records.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_records_count = records.count()

    if selected_scope == 'my':
        recent_records = records.filter(created_by=request.user).select_related(
            'barangay', 'created_by', 'permit_detail', 'project_detail'
        ).prefetch_related(
            'requirements__requirement_item', 'requirements__document'
        ).order_by('-created_at')[:8]
    else:
        recent_records = records.select_related(
            'barangay', 'created_by', 'permit_detail', 'project_detail'
        ).prefetch_related(
            'requirements__requirement_item', 'requirements__document'
        ).order_by('-created_at')[:8]

    # Activity feed
    if request.user.role == 'admin':
        activity_feed = AuditLog.objects.select_related('user').order_by('-performed_at')[:15]
    else:
        activity_feed = AuditLog.objects.filter(user=request.user).select_related('user').order_by('-performed_at')[:15]

    # Recent Uploads
    recent_uploads = Document.objects.select_related('engineering_record', 'uploaded_by').order_by('-uploaded_at')[:5]

    # Incomplete Records list (select created_by for instant JS scope filtering)
    incomplete_list = records.filter(
        requirements__isnull=False,
        requirements__is_fulfilled=False,
        requirements__is_waived=False
    ).distinct().select_related(
        'barangay', 'created_by', 'permit_detail', 'project_detail'
    ).prefetch_related(
        'requirements__requirement_item', 'requirements__document'
    )[:30]


    # Pending records
    pending_records = records.filter(status='pending').select_related('barangay').order_by('-created_at')[:5]

    # Warning alerts context data (grouped, optimized for scalability with preview & count)
    failed_logins_count = 0
    if request.user.role == 'admin':
        failed_logins_count = LoginAttempt.objects.filter(success=False).count()
        
    today_date = timezone.now().date()
    thirty_days_later = today_date + timedelta(days=30)
    
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item')
    
    expired_docs_qs = alert_docs.filter(expiry_date__lt=today_date)
    expired_count = expired_docs_qs.count()
    expired_preview = []
    for doc in expired_docs_qs.order_by('-expiry_date')[:3]:
        doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
        expired_preview.append({
            'label': doc_label,
            'record_title': doc.engineering_record.title,
            'record_id': doc.engineering_record.record_id,
            'expiry_date': doc.expiry_date.strftime('%b %d, %Y'),
        })
        
    expiring_docs_qs = alert_docs.filter(expiry_date__range=(today_date, thirty_days_later))
    expiring_count = expiring_docs_qs.count()
    expiring_preview = []
    for doc in expiring_docs_qs.order_by('expiry_date')[:3]:
        doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
        expiring_preview.append({
            'label': doc_label,
            'record_title': doc.engineering_record.title,
            'record_id': doc.engineering_record.record_id,
            'expiry_date': doc.expiry_date.strftime('%b %d, %Y'),
        })

    alerts = {
        'failed_logins': failed_logins_count,
        'expired_count': expired_count,
        'expired_preview': expired_preview,
        'expiring_count': expiring_count,
        'expiring_preview': expiring_preview,
        'has_alerts': (failed_logins_count > 0 or expired_count > 0 or expiring_count > 0)
    }

    # Charts data
    import json
    # 1. Records per Year (last 5 years)
    years_query = records.filter(year__isnull=False).values('year').annotate(count=Count('record_id')).order_by('year')[:5]
    chart_years = [str(y['year']) for y in years_query]
    chart_year_counts = [y['count'] for y in years_query]

    # 2. Permit Distribution
    permit_query = PermitDetail.objects.values('permit_type').annotate(count=Count('id')).order_by('-count')
    chart_permits = [p['permit_type'] for p in permit_query]
    chart_permit_counts = [p['count'] for p in permit_query]

    # Illegal Construction Tracking Stats
    illegal_qs = records.filter(is_illegal_construction=True)
    illegal_total = illegal_qs.count()
    illegal_unresolved = illegal_qs.filter(illegal_compliance_status='unresolved').count()
    illegal_pending = illegal_qs.filter(illegal_compliance_status='pending_permit').count()
    illegal_resolved = illegal_qs.filter(illegal_compliance_status='resolved').count()
    illegal_recent = illegal_qs.select_related('barangay').order_by('-created_at')[:5]

    # Active users count
    active_users_count = CustomUser.objects.filter(is_active=True).count()
    if active_users_count < 1:
        active_users_count = 1

    # Calculation for Donut Chart (Municipal, Barangay, Permit)
    total_recs = total_records if total_records > 0 else 1
    municipal_pct = round((total_municipal / total_recs) * 100, 1)
    barangay_pct = round((total_barangay / total_recs) * 100, 1)
    permits_pct = round(max(0, 100 - (municipal_pct + barangay_pct)), 1) if (municipal_pct + barangay_pct + round((total_permits / total_recs) * 100, 1)) == 100 else round((total_permits / total_recs) * 100, 1)

    context = {
        'total_permits': total_permits,
        'total_municipal': total_municipal,
        'total_barangay': total_barangay,
        'total_documents': total_documents,
        'total_archived': total_archived,
        'total_records': total_records,
        'active_users_count': active_users_count,
        'municipal_pct': municipal_pct,
        'barangay_pct': barangay_pct,
        'permits_pct': permits_pct,
        'incomplete_records': incomplete_records,
        'recent_records': recent_records,
        'activity_feed': activity_feed,
        'recent_uploads': recent_uploads,
        'incomplete_list': incomplete_list,
        'pending_records': pending_records,
        'illegal_total': illegal_total,
        'illegal_unresolved': illegal_unresolved,
        'illegal_pending': illegal_pending,
        'illegal_resolved': illegal_resolved,
        'illegal_recent': illegal_recent,
        'alerts': alerts,
        'barangays': Barangay.objects.all(),
        'compliance_total': compliance_total,
        'compliance_completed': compliance_completed,
        'compliance_incomplete': compliance_incomplete,
        'compliance_rate': compliance_rate,
        'chart_years_json': json.dumps(chart_years),
        'chart_year_counts_json': json.dumps(chart_year_counts),
        'chart_permits_json': json.dumps(chart_permits),
        'chart_permit_counts_json': json.dumps(chart_permit_counts),
        'selected_scope': selected_scope,
        'my_records_count': my_records_count,
        'all_records_count': all_records_count,
        'active_tab': 'dashboard',
    }
    return render(request, 'permits/dashboard.html', context)


def ensure_barangay_schema():
    """Self-healing helper: Populates 49 PSGC codes and geocoordinates for Carigara barangays if missing."""


    try:
        from permits.models import Barangay
        if Barangay.objects.filter(psgc_code__isnull=False).count() < 49:
            OFFICIAL_49_CARIGARA_BARANGAYS = [
                {"name": "Balilit", "psgc": "0803715001", "lat": 11.2874, "lng": 124.6950},
                {"name": "Barayong", "psgc": "0803715002", "lat": 11.2682, "lng": 124.6722},
                {"name": "Barugohay Central", "psgc": "0803715003", "lat": 11.2960, "lng": 124.6986},
                {"name": "Barugohay Norte", "psgc": "0803715004", "lat": 11.3029, "lng": 124.7050},
                {"name": "Barugohay Sur", "psgc": "0803715005", "lat": 11.2720, "lng": 124.6994},
                {"name": "Baybay (Poblacion)", "psgc": "0803715006", "lat": 11.3011, "lng": 124.6889},
                {"name": "Binibihan", "psgc": "0803715007", "lat": 11.2334, "lng": 124.7336},
                {"name": "Bislig", "psgc": "0803715008", "lat": 11.2923, "lng": 124.6769},
                {"name": "Caghalo", "psgc": "0803715009", "lat": 11.2611, "lng": 124.6676},
                {"name": "Camansi", "psgc": "0803715010", "lat": 11.2188, "lng": 124.7159},
                {"name": "Canal", "psgc": "0803715011", "lat": 11.2878, "lng": 124.6826},
                {"name": "Candigahub", "psgc": "0803715012", "lat": 11.2501, "lng": 124.7007},
                {"name": "Canlampay", "psgc": "0803715013", "lat": 11.2649, "lng": 124.6848},
                {"name": "Cogon", "psgc": "0803715014", "lat": 11.2577, "lng": 124.7365},
                {"name": "Cutay", "psgc": "0803715015", "lat": 11.2649, "lng": 124.6987},
                {"name": "East Visoria", "psgc": "0803715016", "lat": 11.3017, "lng": 124.6826},
                {"name": "Guindapunan East", "psgc": "0803715017", "lat": 11.3037, "lng": 124.7004},
                {"name": "Guindapunan West", "psgc": "0803715018", "lat": 11.3026, "lng": 124.6980},
                {"name": "Hiluctogan", "psgc": "0803715019", "lat": 11.2471, "lng": 124.6877},
                {"name": "Jugaban (Poblacion)", "psgc": "0803715020", "lat": 11.3007, "lng": 124.6934},
                {"name": "Libo", "psgc": "0803715021", "lat": 11.2671, "lng": 124.6809},
                {"name": "Lower Hiraan", "psgc": "0803715022", "lat": 11.2795, "lng": 124.6786},
                {"name": "Lower Sogod", "psgc": "0803715023", "lat": 11.2572, "lng": 124.6903},
                {"name": "Macalpi", "psgc": "0803715024", "lat": 11.2126, "lng": 124.7332},
                {"name": "Manloy", "psgc": "0803715025", "lat": 11.2750, "lng": 124.6636},
                {"name": "Nauguisan", "psgc": "0803715026", "lat": 11.2955, "lng": 124.6637},
                {"name": "Pangna", "psgc": "0803715027", "lat": 11.2798, "lng": 124.7101},
                {"name": "Parag-um", "psgc": "0803715028", "lat": 11.2575, "lng": 124.7279},
                {"name": "Parena (Parina)", "psgc": "0803715029", "lat": 11.2979, "lng": 124.7121},
                {"name": "Piloro", "psgc": "0803715030", "lat": 11.2365, "lng": 124.7205},
                {"name": "Ponong (Poblacion)", "psgc": "0803715031", "lat": 11.2977, "lng": 124.6829},
                {"name": "Sagkahan", "psgc": "0803715032", "lat": 11.2799, "lng": 124.7260},
                {"name": "San Mateo (Poblacion)", "psgc": "0803715033", "lat": 11.3018, "lng": 124.6953},
                {"name": "Santa Fe", "psgc": "0803715034", "lat": 11.2567, "lng": 124.7151},
                {"name": "Sawang (Poblacion)", "psgc": "0803715035", "lat": 11.2993, "lng": 124.6895},
                {"name": "Tagak", "psgc": "0803715036", "lat": 11.2891, "lng": 124.7122},
                {"name": "Tangnan", "psgc": "0803715037", "lat": 11.2982, "lng": 124.6713},
                {"name": "Tigbao", "psgc": "0803715038", "lat": 11.2379, "lng": 124.7132},
                {"name": "Tinaguban", "psgc": "0803715039", "lat": 11.2382, "lng": 124.7018},
                {"name": "Upper Hiraan", "psgc": "0803715040", "lat": 11.2648, "lng": 124.6759},
                {"name": "Upper Sogod", "psgc": "0803715041", "lat": 11.2536, "lng": 124.6931},
                {"name": "Uyawan", "psgc": "0803715042", "lat": 11.2841, "lng": 124.6844},
                {"name": "West Visoria", "psgc": "0803715043", "lat": 11.2991, "lng": 124.6769},
                {"name": "Paglaum", "psgc": "0803715044", "lat": 11.2045, "lng": 124.7188},
                {"name": "San Juan", "psgc": "0803715045", "lat": 11.2888, "lng": 124.6611},
                {"name": "Bagong Lipunan", "psgc": "0803715046", "lat": 11.2843, "lng": 124.6987},
                {"name": "Canfabi", "psgc": "0803715047", "lat": 11.2654, "lng": 124.7092},
                {"name": "Rizal (Tagak East)", "psgc": "0803715048", "lat": 11.2867, "lng": 124.7172},
                {"name": "San Isidro", "psgc": "0803715049", "lat": 11.2054, "lng": 124.7082}
            ]
            for item in OFFICIAL_49_CARIGARA_BARANGAYS:
                name = item["name"]
                psgc = item["psgc"]
                lat = item["lat"]
                lng = item["lng"]
                b = Barangay.objects.filter(barangay_name__iexact=name).first()
                if not b:
                    short_name = name.replace(" (Poblacion)", "").strip()
                    b = Barangay.objects.filter(barangay_name__iexact=short_name).first()
                if not b:
                    Barangay.objects.create(barangay_name=name, psgc_code=psgc, latitude=lat, longitude=lng)
                else:
                    b.barangay_name = name
                    b.psgc_code = psgc
                    b.latitude = lat
                    b.longitude = lng
                    b.save()
            OFFICIAL_NAMES = [item["name"] for item in OFFICIAL_49_CARIGARA_BARANGAYS]
            Barangay.objects.filter(Q(barangay_name__in=['1', '2333333333', 'test']) | Q(barangay_name__regex=r'^\d+$')).delete()
            Barangay.objects.exclude(barangay_name__in=OFFICIAL_NAMES).filter(engineering_records__isnull=True, records__isnull=True).delete()
    except Exception:
        pass


# ─── BARANGAYS ───────────────────────────────────────────────────────────────

@login_required
def barangays_view(request):
    ensure_barangay_schema()

    # Clean up non-official test entries if present
    OFFICIAL_NAMES = [
        "Bagong Lipunan", "Balilit", "Barayong", "Barugohay Central", "Barugohay Norte", "Barugohay Sur",
        "Baybay (Poblacion)", "Binibihan", "Bislig", "Caghalo", "Camansi", "Canal", "Candigahub", "Canfabi",
        "Canlampay", "Cogon", "Cutay", "East Visoria", "Guindapunan East", "Guindapunan West", "Hiluctogan",
        "Jugaban (Poblacion)", "Libo", "Lower Hiraan", "Lower Sogod", "Macalpi", "Manloy", "Nauguisan",
        "Paglaum", "Pangna", "Parag-um", "Parena (Parina)", "Piloro", "Ponong (Poblacion)", "Rizal (Tagak East)",
        "Sagkahan", "San Isidro", "San Juan", "San Mateo (Poblacion)", "Santa Fe", "Sawang (Poblacion)",
        "Tagak", "Tangnan", "Tigbao", "Tinaguban", "Upper Hiraan", "Upper Sogod", "Uyawan", "West Visoria"
    ]
    Barangay.objects.filter(Q(barangay_name__in=['1', '2333333333', 'test']) | Q(barangay_name__regex=r'^\d+$')).delete()
    Barangay.objects.exclude(barangay_name__in=OFFICIAL_NAMES).filter(engineering_records__isnull=True, records__isnull=True).delete()

    if request.method == 'POST':
        action = request.POST.get('action')
        if request.user.role not in ['admin', 'staff']:
            return HttpResponseForbidden("Unauthorized")

        if action == 'add_barangay':
            name = request.POST.get('barangay_name', '').strip()
            latitude = request.POST.get('latitude', '').strip()
            longitude = request.POST.get('longitude', '').strip()
            if name:
                if Barangay.objects.filter(barangay_name__iexact=name).exists():
                    messages.error(request, f"Barangay '{name}' already exists.")
                else:
                    lat_val = float(latitude) if latitude else None
                    lng_val = float(longitude) if longitude else None
                    b = Barangay.objects.create(
                        barangay_name=name,
                        latitude=lat_val,
                        longitude=lng_val
                    )
                    log_audit(request.user, f"Created Barangay '{b.barangay_name}'", request=request)
                    messages.success(request, f"Barangay '{b.barangay_name}' has been created successfully.")
            return redirect('barangays')

        elif action == 'edit_barangay':
            barangay_id = request.POST.get('barangay_id')
            name = request.POST.get('barangay_name', '').strip()
            latitude = request.POST.get('latitude', '').strip()
            longitude = request.POST.get('longitude', '').strip()
            if barangay_id and name:
                barangay = get_object_or_404(Barangay, barangay_id=barangay_id)
                if Barangay.objects.filter(barangay_name__iexact=name).exclude(barangay_id=barangay_id).exists():
                    messages.error(request, f"Another barangay named '{name}' already exists.")
                else:
                    old_name = barangay.barangay_name
                    barangay.barangay_name = name
                    if latitude:
                        try: barangay.latitude = float(latitude)
                        except (ValueError, TypeError): pass
                    if longitude:
                        try: barangay.longitude = float(longitude)
                        except (ValueError, TypeError): pass
                    barangay.save()
                    log_audit(request.user, f"Updated Barangay '{name}'", request=request)
                    messages.success(request, f"Barangay '{name}' updated successfully.")
            return redirect('barangays')

        elif action == 'delete_barangay':
            barangay_id = request.POST.get('barangay_id')
            if barangay_id:
                barangay = get_object_or_404(Barangay, barangay_id=barangay_id)
                records_count = barangay.engineering_records.count() + barangay.records.count()
                if records_count > 0:
                    messages.error(request, f"Cannot delete '{barangay.barangay_name}' because it contains {records_count} active record(s).")
                else:
                    name = barangay.barangay_name
                    barangay.delete()
                    log_audit(request.user, f"Deleted Barangay '{name}'", request=request)
                    messages.success(request, f"Barangay '{name}' deleted successfully.")
            return redirect('barangays')

    sort = request.GET.get('sort', 'a-z').strip().lower()
    query = request.GET.get('q', '').strip()

    base_qs = Barangay.objects.annotate(
        total_records=Count('engineering_records', filter=~Q(engineering_records__status='archived')),
        permit_count=Count('engineering_records', filter=Q(engineering_records__record_type='Permit') & ~Q(engineering_records__status='archived')),
        project_count=Count('engineering_records', filter=Q(engineering_records__record_type='Project') & ~Q(engineering_records__status='archived')),
    )

    if query:
        filtered_qs = base_qs.filter(barangay_name__icontains=query)
    else:
        filtered_qs = base_qs

    if sort == 'z-a':
        barangays = filtered_qs.order_by('-barangay_name')
    elif sort == 'most_records':
        barangays = filtered_qs.order_by('-total_records', 'barangay_name')
    elif sort == 'fewest_records':
        barangays = filtered_qs.order_by('total_records', 'barangay_name')
    else:
        sort = 'a-z'
        barangays = filtered_qs.order_by('barangay_name')

    total_barangays_count = Barangay.objects.count()
    shown_barangays_count = barangays.count()


    context = {
        'barangays': barangays,
        'q': query,
        'sort': sort,
        'total_barangays_count': total_barangays_count,
        'shown_barangays_count': shown_barangays_count,
        'active_tab': 'barangays',
    }
    return render(request, 'permits/barangays.html', context)



@login_required
def barangay_workspace_view(request, barangay_id):
    ensure_barangay_schema()
    barangay = get_object_or_404(Barangay, barangay_id=barangay_id)
    records = EngineeringRecord.objects.filter(barangay=barangay).exclude(status='archived').select_related(
        'created_by', 'barangay', 'permit_detail', 'project_detail'
    ).prefetch_related(
        'requirements__requirement_item', 'requirements__document'
    )

    # Stats
    total_permits = records.filter(record_type='Permit').count()
    total_projects = records.filter(record_type='Project').count()
    total_documents = Document.objects.filter(engineering_record__barangay=barangay).count()

    # Tab filter
    tab = request.GET.get('tab', 'all')
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    
    filtered_records = records
    if tab == 'permits':
        filtered_records = filtered_records.filter(record_type='Permit')
    elif tab == 'projects':
        filtered_records = filtered_records.filter(record_type='Project')

    if query:
        filtered_records = filtered_records.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    if status_filter:
        filtered_records = filtered_records.filter(status=status_filter)

    filtered_records = filtered_records.order_by('-created_at')

    # Permits breakdown
    permit_breakdown = PermitDetail.objects.filter(
        engineering_record__barangay=barangay
    ).values('permit_type').annotate(count=Count('id')).order_by('-count')

    # Project breakdown
    project_breakdown = ProjectDetail.objects.filter(
        engineering_record__barangay=barangay
    ).values('project_type').annotate(count=Count('id')).order_by('-count')

    # Recent activity
    record_ids = records.values_list('record_id', flat=True)
    recent_activity = AuditLog.objects.filter(
        target_record_id__in=record_ids
    ).select_related('user').order_by('-performed_at')[:10]

    per_page = get_per_page(request, 10)
    paginator = Paginator(filtered_records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Dynamic Nearby Barangays calculation via Haversine distance
    import math
    nearby_barangays = []
    if barangay.latitude and barangay.longitude:
        b_lat, b_lng = barangay.latitude, barangay.longitude
        all_other = Barangay.objects.exclude(barangay_id=barangay.barangay_id).filter(
            latitude__isnull=False, longitude__isnull=False
        )
        
        calculated_list = []
        for b_item in all_other:
            dlat = math.radians(b_item.latitude - b_lat)
            dlon = math.radians(b_item.longitude - b_lng)
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(b_lat)) * math.cos(math.radians(b_item.latitude)) * math.sin(dlon / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_km = round(6371.0 * c, 2)
            calculated_list.append({
                'barangay': b_item,
                'distance_km': dist_km
            })
            
        calculated_list.sort(key=lambda x: x['distance_km'])
        nearby_barangays = calculated_list[:4]

    context = {
        'per_page': per_page,
        'barangay': barangay,
        'nearby_barangays': nearby_barangays,
        'total_permits': total_permits,
        'total_projects': total_projects,
        'total_documents': total_documents,
        'total_records': total_permits + total_projects,
        'permit_breakdown': permit_breakdown,
        'project_breakdown': project_breakdown,
        'recent_activity': recent_activity,
        'page_obj': page_obj,
        'current_tab': tab,
        'q': query,
        'selected_status': status_filter,
        'active_tab': 'barangays',
    }
    return render(request, 'permits/barangay_workspace.html', context)


# ─── ENGINEERING RECORDS (BROWSE ALL) ────────────────────────────────────────

@login_required
def records_browse_view(request):
    illegal_filter = request.GET.get('illegal', '').strip()
    record_type = request.GET.get('record_type', '')
    if illegal_filter or record_type == 'Illegal':
        url = reverse('illegal_constructions')
        params = request.GET.copy()
        if 'illegal' in params:
            del params['illegal']
        if params.get('record_type') == 'Illegal':
            del params['record_type']
        qstr = params.urlencode()
        return redirect(f"{url}?{qstr}" if qstr else url)

    base_records = EngineeringRecord.objects.exclude(status='archived').select_related(
        'barangay', 'created_by', 'permit_detail', 'project_detail'
    ).prefetch_related(
        'requirements__requirement_item', 'requirements__document'
    )
    barangays = Barangay.objects.all()

    # Filters
    query = request.GET.get('q', '').strip()
    project_scope = request.GET.get('project_scope', '')
    barangay_id = request.GET.get('barangay', '')
    status = request.GET.get('status', '')
    year = request.GET.get('year', '')
    
    project_type = request.GET.get('project_type', '').strip()
    permit_type = request.GET.get('permit_type', '').strip()

    # 1. Compute unfiltered base for stable count statistics across regular tabs
    unfiltered_base = filter_engineering_records(
        base_records,
        query=query,
        barangay_id=barangay_id,
        status=status,
        year=year,
        permit_type=permit_type,
        project_type=project_type,
        illegal_filter=None
    )

    # Scope resolution
    selected_scope = resolve_scope(request)
    my_scope_count = unfiltered_base.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_scope_count = unfiltered_base.count()

    if selected_scope == 'my':
        unfiltered_base = unfiltered_base.filter(created_by=request.user)

    # 2. Compute TRUE STABLE COUNTS for top tabs
    all_count = unfiltered_base.count()
    municipal_count = unfiltered_base.filter(record_type='Project', project_scope='Municipal').count()
    barangay_count = unfiltered_base.filter(record_type='Project', project_scope='Barangay').count()
    permits_count = unfiltered_base.filter(record_type='Permit').count()

    # 3. Apply active tab & sub-filter to get the final records list
    records = filter_engineering_records(
        unfiltered_base,
        record_type=record_type,
        illegal_filter=None
    )
    if selected_scope == 'my':
        records = records.filter(created_by=request.user)
    if project_scope and record_type == 'Project':
        records = records.filter(project_scope=project_scope)

    total_count = records.count()
    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    year_choices = get_year_choices()

    # Calculate active advanced filters count (only count optional dropdown filters)
    active_filters_count = sum(1 for val in [barangay_id, status, year, project_type, permit_type] if val)

    context = {
        'per_page': per_page,
        'barangays': barangays,
        'page_obj': page_obj,
        'total_count': total_count,
        'all_count': all_count,
        'municipal_count': municipal_count,
        'barangay_count': barangay_count,
        'permits_count': permits_count,
        'active_filters_count': active_filters_count,
        'q': query,
        'selected_record_type': record_type,
        'selected_scope': selected_scope,
        'my_scope_count': my_scope_count,
        'all_scope_count': all_scope_count,
        'selected_project_scope': project_scope,
        'selected_barangay': barangay_id,
        'selected_status': status,
        'selected_year': year,
        'selected_project_type': project_type,
        'selected_permit_type': permit_type,
        'year_choices': year_choices,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'project_type_choices': [choice[0] for choice in ProjectDetail.PROJECT_TYPE_CHOICES],
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'active_tab': 'records',
    }
    return render(request, 'permits/records_browse.html', context)


@login_required
def illegal_constructions_view(request):
    """
    Dedicated Standalone Case Management View for Illegal Construction Incidents.
    Tracks unresolved violations (Stop Orders / Notices to Comply), applications filed, and regularized cases.
    """
    base_records = EngineeringRecord.objects.exclude(status='archived').filter(
        is_illegal_construction=True
    ).select_related(
        'barangay', 'created_by', 'permit_detail', 'project_detail'
    ).prefetch_related(
        'requirements__requirement_item', 'requirements__document', 'documents'
    )
    barangays = Barangay.objects.all()

    query = request.GET.get('q', '').strip()
    barangay_id = request.GET.get('barangay', '')
    year = request.GET.get('year', '')
    stage_filter = request.GET.get('stage', '').strip()  # 'unresolved', 'pending_permit', 'resolved'

    # Filter base
    qs = base_records
    if query:
        search_filter = (
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(barangay__barangay_name__icontains=query) |
            Q(permit_detail__applicant_name__icontains=query) |
            Q(created_by__full_name__icontains=query) |
            Q(created_by__username__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query)) | Q(created_at__year=int(query)) | Q(date_started__year=int(query))
        qs = qs.filter(search_filter).distinct()

    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except (ValueError, TypeError):
            qs = qs.filter(year=year)

    selected_scope = resolve_scope(request)
    my_scope_count = qs.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_scope_count = qs.count()

    if selected_scope == 'my':
        qs = qs.filter(created_by=request.user)

    # Incident status metrics
    all_count = qs.count()
    unresolved_count = qs.filter(illegal_compliance_status='unresolved').count()
    pending_count = qs.filter(illegal_compliance_status='pending_permit').count()
    resolved_count = qs.filter(illegal_compliance_status='resolved').count()

    # Stage filtering
    if stage_filter in ['unresolved', 'pending_permit', 'resolved']:
        records = qs.filter(illegal_compliance_status=stage_filter)
    else:
        records = qs

    total_count = records.count()
    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    year_choices = get_year_choices()
    active_filters_count = sum(1 for val in [barangay_id, year, stage_filter] if val)

    context = {
        'per_page': per_page,
        'barangays': barangays,
        'page_obj': page_obj,
        'total_count': total_count,
        'all_count': all_count,
        'unresolved_count': unresolved_count,
        'pending_count': pending_count,
        'resolved_count': resolved_count,
        'stage_filter': stage_filter,
        'active_filters_count': active_filters_count,
        'q': query,
        'selected_scope': selected_scope,
        'my_scope_count': my_scope_count,
        'all_scope_count': all_scope_count,
        'selected_barangay': barangay_id,
        'selected_year': year,
        'year_choices': year_choices,
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'active_tab': 'illegal',
    }
    return render(request, 'permits/illegal_constructions.html', context)



# ─── CREATE RECORD — STEP 1: CATEGORY ────────────────────────────────────────


@login_required

@login_required
def record_create_step1_view(request):
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to encode records.")
    
    # Pre-select category via GET parameter for quick actions
    cat_param = request.GET.get('category')
    if cat_param in ['municipal', 'barangay', 'permit']:
        request.session['create_category'] = cat_param
        return redirect('create_step2')
        
    if request.method == 'POST':
        category = request.POST.get('category')
        if category in ['municipal', 'barangay', 'permit']:
            request.session['create_category'] = category
            return redirect('create_step2')
        messages.error(request, "Invalid category selection.")
    
    return render(request, 'permits/create_step1.html', {
        'active_tab': 'records'
    })

@login_required
def record_create_step2_view(request):
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to encode records.")
    
    category = request.session.get('create_category')
    if not category:
        return redirect('create_step1')
    
    if category == 'permit':
        types = [
            {'value': 'Building', 'label': 'Building Permit', 'icon': 'fa-solid fa-building', 'desc': 'Standard building permit structure approvals.'},
            {'value': 'Electrical', 'label': 'Electrical Permit', 'icon': 'fa-solid fa-bolt', 'desc': 'Electrical wiring and electrical installation approvals.'},
            {'value': 'Occupancy', 'label': 'Occupancy Permit', 'icon': 'fa-solid fa-house-chimney-user', 'desc': 'Certificate of occupancy approvals.'},
            {'value': 'Fencing', 'label': 'Fencing Permit', 'icon': 'fa-solid fa-border-all', 'desc': 'Fencing installation clearances.'},
        ]
    else:
        types = [
            {'value': 'Road & Bridge', 'label': 'Road & Bridge', 'icon': 'fa-solid fa-road', 'desc': 'Road concreting, bridges, and pathways.'},
            {'value': 'Building', 'label': 'Building', 'icon': 'fa-solid fa-building-columns', 'desc': 'Government buildings, gyms, or centers.'},
            {'value': 'Water System', 'label': 'Water System', 'icon': 'fa-solid fa-droplet', 'desc': 'Water lines, wells, and irrigation projects.'},
            {'value': 'Flood Control', 'label': 'Flood Control', 'icon': 'fa-solid fa-shield-halved', 'desc': 'Seawalls, dikes, and revetments.'},
            {'value': 'Drainage', 'label': 'Drainage', 'icon': 'fa-solid fa-arrows-split-up-and-left', 'desc': 'Drainage lines and culverts.'},
            {'value': 'Multi-purpose Hall', 'label': 'Multi-purpose Hall', 'icon': 'fa-solid fa-house-flag', 'desc': 'Community halls and gymnasiums.'},
            {'value': 'Others', 'label': 'Others', 'icon': 'fa-solid fa-folder', 'desc': 'Other public infrastructure works.'},
        ]
    
    if request.method == 'POST':
        subtype = request.POST.get('record_subtype')
        if subtype:
            request.session['create_subtype'] = subtype
            return redirect('create_step3')
        messages.error(request, "Please select a type.")
        
    return render(request, 'permits/create_step2.html', {
        'category': category,
        'types': types,
        'active_tab': 'records'
    })

@login_required
def record_create_step3_view(request):
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to encode records.")
    
    category = request.session.get('create_category')
    subtype = request.session.get('create_subtype')
    if not category or not subtype:
        return redirect('create_step1')
    
    barangays = Barangay.objects.all()
    scope = 'Municipal' if category == 'municipal' else ('Barangay' if category == 'barangay' else '')
    record_type = 'Permit' if category == 'permit' else 'Project'
    
    template = RequirementTemplate.objects.filter(
        record_type=record_type, subtype=subtype, scope=scope, is_active=True
    ).first()
    
    context_extra = {
        'category': category,
        'subtype': subtype,
        'scope': scope,
        'barangays': barangays,
        'template': template,
        'current_year': timezone.now().year,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
        'funding_sources': ProjectDetail.FUNDING_SOURCE_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'active_tab': 'records'
    }

    if request.method == 'POST':
        barangay_id = request.POST.get('barangay')
        year = request.POST.get('year') or None
        status = request.POST.get('status', 'active')
        
        current_year = timezone.now().year
        if year:
            try:
                year_val = int(year)
                if year_val > current_year:
                    messages.error(request, f"Filing year cannot be in the future (max {current_year}).")
                    return render(request, 'permits/create_step3.html', context_extra)
            except ValueError:
                messages.error(request, "Invalid year value.")
                return render(request, 'permits/create_step3.html', context_extra)
        
        if category == 'permit':
            applicant_name = sanitize_input(request.POST.get('applicant_name', '')).strip()
            if not applicant_name:
                messages.error(request, "Applicant / Property Owner name is required for permits.")
                return render(request, 'permits/create_step3.html', context_extra)
            permit_number = sanitize_input(request.POST.get('permit_number', '')).strip()
            title = permit_number + ' — ' + applicant_name if permit_number else applicant_name
        else:
            title = sanitize_input(request.POST.get('title', '')).strip()
            contractor_val = sanitize_input(request.POST.get('contractor', '')).strip()
            if not contractor_val:
                messages.error(request, "Contractor or Implementing Entity is required for projects (or specify 'By Administration').")
                return render(request, 'permits/create_step3.html', context_extra)
            
        if not barangay_id or not title or not year:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'permits/create_step3.html', context_extra)
            
        is_illegal = request.POST.get('is_illegal_construction') == 'on' or request.POST.get('is_illegal_construction') == 'true'
        illegal_status = request.POST.get('illegal_compliance_status', 'unresolved') if is_illegal else 'unresolved'

        lat_raw = request.POST.get('latitude', '').strip()
        lng_raw = request.POST.get('longitude', '').strip()
        lat_val = float(lat_raw) if lat_raw else None
        lng_val = float(lng_raw) if lng_raw else None

        record = EngineeringRecord.objects.create(
            record_type=record_type,
            project_scope=scope,
            barangay_id=barangay_id,
            title=title,
            year=year,
            description=sanitize_input(request.POST.get('description', '')).strip() if category != 'permit' else '',
            status=status,
            is_illegal_construction=is_illegal,
            illegal_compliance_status=illegal_status,
            latitude=lat_val,
            longitude=lng_val,
            created_by=request.user,
        )

        
        if record_type == 'Permit':
            date_issued_val = request.POST.get('date_issued', '').strip() or None
            PermitDetail.objects.create(
                engineering_record=record,
                permit_type=subtype,
                building_type=request.POST.get('building_type', ''),
                permit_number=permit_number,
                applicant_name=applicant_name,
                date_issued=date_issued_val,
                remarks=sanitize_input(request.POST.get('remarks', '')).strip(),
            )
        elif record_type == 'Project':
            project_status = request.POST.get('project_status', 'Planning')
            funding_val = sanitize_input(request.POST.get('funding_source', 'General Fund')).strip()
            funding_other_val = sanitize_input(request.POST.get('funding_source_other', '')).strip() if funding_val == 'Others' else ''
            
            ProjectDetail.objects.create(
                engineering_record=record,
                project_type=subtype,
                funding_source=funding_val or 'General Fund',
                funding_source_other=funding_other_val,
                contractor=sanitize_input(request.POST.get('contractor', '')).strip(),
                project_cost=parse_decimal_safely(request.POST.get('project_cost')),
                project_status=project_status,
            )
            # Sync parent record status
            if project_status == 'Completed':
                record.status = 'completed'
            elif project_status == 'Ongoing':
                record.status = 'in_progress'
            else:
                record.status = 'active'
            record.save()
            
        if template:
            RecordRequirement.objects.bulk_create([
                RecordRequirement(record=record, requirement_item=item)
                for item in template.active_items
            ])
            
        request.session.pop('create_category', None)
        request.session.pop('create_subtype', None)
        
        log_audit(
            request.user,
            f"Created {record_type} record: '{title}'",
            record.record_id, request
        )
        messages.success(request, f"Record '{title}' created successfully! Check list is ready.")
        return redirect('record_detail', record_id=record.record_id)
        
    return render(request, 'permits/create_step3.html', context_extra)



# ─── MODULE LIST VIEWS ────────────────────────────────────────────────────────

@login_required
def municipal_projects_view(request):
    """Lists all Municipal Project records."""
    selected_scope = resolve_scope(request)
    base_qs = EngineeringRecord.objects.filter(
        record_type='Project', project_scope='Municipal'
    ).exclude(status='archived')

    my_scope_count = base_qs.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_scope_count = base_qs.count()

    if selected_scope == 'my':
        base_qs = base_qs.filter(created_by=request.user)

    records = base_qs.select_related('barangay', 'created_by', 'project_detail').order_by('-created_at')

    query = request.GET.get('q', '').strip()
    project_type = request.GET.get('project_type', '')
    status = request.GET.get('status', '')
    year = request.GET.get('year', '')
    barangay_id = request.GET.get('barangay', '')

    if query:
        search_filter = (
            Q(title__icontains=query) |
            Q(barangay__barangay_name__icontains=query) |
            Q(project_detail__contractor__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query))
        records = records.filter(search_filter).distinct()
    if project_type:
        records = records.filter(project_detail__project_type=project_type)
    if status:
        records = records.filter(status=status)
    if year:
        try:
            records = records.filter(year=int(year))
        except (ValueError, TypeError):
            records = records.filter(year=year)
    if barangay_id:
        records = records.filter(barangay_id=barangay_id)

    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    year_choices = get_year_choices()
    active_filters_count = sum(1 for val in [project_type, status, year, barangay_id] if val)

    context = {
        'per_page': per_page,
        'page_obj': page_obj,
        'q': query,
        'selected_project_type': project_type,
        'selected_status': status,
        'selected_year': year,
        'selected_barangay': barangay_id,
        'selected_scope': selected_scope,
        'my_scope_count': my_scope_count,
        'all_scope_count': all_scope_count,
        'project_types': ProjectDetail.PROJECT_TYPE_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'barangays': Barangay.objects.all(),
        'year_choices': year_choices,
        'active_filters_count': active_filters_count,
        'module_title': 'Municipal Projects',
        'module_scope': 'Municipal',
        'active_tab': 'municipal',
    }
    return render(request, 'permits/module_projects.html', context)


@login_required
def barangay_projects_view(request):
    """Lists all Barangay Project records."""
    selected_scope = resolve_scope(request)
    base_qs = EngineeringRecord.objects.filter(
        record_type='Project', project_scope='Barangay'
    ).exclude(status='archived')

    my_scope_count = base_qs.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_scope_count = base_qs.count()

    if selected_scope == 'my':
        base_qs = base_qs.filter(created_by=request.user)

    records = base_qs.select_related('barangay', 'created_by', 'project_detail').order_by('-created_at')

    query = request.GET.get('q', '').strip()
    project_type = request.GET.get('project_type', '')
    status = request.GET.get('status', '')
    year = request.GET.get('year', '')
    barangay_id = request.GET.get('barangay', '')

    if query:
        search_filter = (
            Q(title__icontains=query) |
            Q(barangay__barangay_name__icontains=query) |
            Q(project_detail__contractor__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query))
        records = records.filter(search_filter).distinct()
    if project_type:
        records = records.filter(project_detail__project_type=project_type)
    if status:
        records = records.filter(status=status)
    if year:
        try:
            records = records.filter(year=int(year))
        except (ValueError, TypeError):
            records = records.filter(year=year)
    if barangay_id:
        records = records.filter(barangay_id=barangay_id)

    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    year_choices = get_year_choices()
    active_filters_count = sum(1 for val in [project_type, status, year, barangay_id] if val)

    context = {
        'per_page': per_page,
        'page_obj': page_obj,
        'q': query,
        'selected_project_type': project_type,
        'selected_status': status,
        'selected_year': year,
        'selected_barangay': barangay_id,
        'selected_scope': selected_scope,
        'my_scope_count': my_scope_count,
        'all_scope_count': all_scope_count,
        'project_types': ProjectDetail.PROJECT_TYPE_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'barangays': Barangay.objects.all(),
        'year_choices': year_choices,
        'active_filters_count': active_filters_count,
        'module_title': 'Barangay Projects',
        'module_scope': 'Barangay',
        'active_tab': 'barangay',
    }
    return render(request, 'permits/module_projects.html', context)


@login_required
def permit_records_view(request):
    """Lists all Permit records."""
    selected_scope = resolve_scope(request)
    base_qs = EngineeringRecord.objects.filter(
        record_type='Permit'
    ).exclude(status='archived')

    my_scope_count = base_qs.filter(created_by=request.user).count() if request.user.is_authenticated else 0
    all_scope_count = base_qs.count()

    if selected_scope == 'my':
        base_qs = base_qs.filter(created_by=request.user)

    records = base_qs.select_related('barangay', 'created_by', 'permit_detail').order_by('-created_at')

    query = request.GET.get('q', '').strip()
    permit_type = request.GET.get('permit_type', '')
    status = request.GET.get('status', '')
    year = request.GET.get('year', '')
    barangay_id = request.GET.get('barangay', '')

    if query:
        search_filter = (
            Q(title__icontains=query) |
            Q(permit_detail__applicant_name__icontains=query) |
            Q(permit_detail__permit_number__icontains=query) |
            Q(barangay__barangay_name__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query))
        records = records.filter(search_filter).distinct()
    if permit_type:
        records = records.filter(permit_detail__permit_type=permit_type)
    if status:
        records = records.filter(status=status)
    if year:
        try:
            records = records.filter(year=int(year))
        except (ValueError, TypeError):
            records = records.filter(year=year)
    if barangay_id:
        records = records.filter(barangay_id=barangay_id)

    # Count complete vs pending permits for status line
    pending_count = 0
    complete_count = 0
    for r in records:
        if r.completion_stats['is_complete']:
            complete_count += 1
        else:
            pending_count += 1

    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    year_choices = get_year_choices()
    active_filters_count = sum(1 for val in [permit_type, status, year, barangay_id] if val)

    context = {
        'per_page': per_page,
        'page_obj': page_obj,
        'q': query,
        'selected_permit_type': permit_type,
        'selected_status': status,
        'selected_year': year,
        'selected_barangay': barangay_id,
        'selected_scope': selected_scope,
        'my_scope_count': my_scope_count,
        'all_scope_count': all_scope_count,
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'barangays': Barangay.objects.all(),
        'year_choices': year_choices,
        'active_filters_count': active_filters_count,
        'module_title': 'Permit Applications',
        'active_tab': 'permits',
        'pending_count': pending_count,
        'complete_count': complete_count,
    }
    return render(request, 'permits/module_permits.html', context)


# ─── CREATE RECORD (SINGLE PAGE FORM) ──────────────────────────────────────────

@login_required
def record_create_view(request):
    """Unified single-page form to create record and load checklist instantly."""
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to encode records.")

    barangays = Barangay.objects.all()

    if request.method == 'POST':
        category = request.POST.get('category', '')
        subtype = request.POST.get('subtype', '')
        barangay_id = request.POST.get('barangay', '')
        year = request.POST.get('year', '') or None
        status = request.POST.get('status', 'active')
        
        current_year = timezone.now().year
        if year:
            try:
                year_val = int(year)
                if year_val > current_year:
                    messages.error(request, f"Filing year cannot be in the future (max {current_year}).")
                    return render(request, 'permits/create_record.html', {
                        'barangays': barangays,
                        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
                        'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
                        'status_choices': EngineeringRecord.STATUS_CHOICES,
                        'current_year': current_year,
                        'active_tab': 'records',
                    })
            except ValueError:
                messages.error(request, "Invalid year value.")
                return render(request, 'permits/create_record.html', {
                    'barangays': barangays,
                    'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
                    'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
                    'status_choices': EngineeringRecord.STATUS_CHOICES,
                    'current_year': current_year,
                    'active_tab': 'records',
                })

        # Resolve title
        if category == 'permit':
            applicant_name = sanitize_input(request.POST.get('applicant_name', '')).strip()
            permit_number = sanitize_input(request.POST.get('permit_number', '')).strip()
            title = sanitize_input(request.POST.get('permit_title', '')).strip()
            if not title:
                title = permit_number + ' — ' + applicant_name if permit_number else applicant_name
            record_type = 'Permit'
            scope = ''
        else:
            title = sanitize_input(request.POST.get('title', '')).strip()
            record_type = 'Project'
            scope = 'Municipal' if category == 'municipal' else 'Barangay'

        if not category or not subtype or not barangay_id or not title:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'permits/create_record.html', {
                'barangays': barangays,
                'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
                'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
                'status_choices': EngineeringRecord.STATUS_CHOICES,
                'current_year': timezone.now().year,
                'active_tab': 'records',
            })

        is_illegal = request.POST.get('is_illegal_construction') == 'on' or request.POST.get('is_illegal_construction') == 'true'
        illegal_status = request.POST.get('illegal_compliance_status', 'unresolved') if is_illegal else 'unresolved'

        lat_raw = request.POST.get('latitude', '').strip()
        lng_raw = request.POST.get('longitude', '').strip()
        lat_val = float(lat_raw) if lat_raw else None
        lng_val = float(lng_raw) if lng_raw else None

        # Save record
        record = EngineeringRecord.objects.create(
            record_type=record_type,
            project_scope=scope,
            barangay_id=barangay_id,
            title=title,
            year=year,
            description=sanitize_input(request.POST.get('description', '')).strip() if category != 'permit' else '',
            status=status,
            is_illegal_construction=is_illegal,
            illegal_compliance_status=illegal_status,
            latitude=lat_val,
            longitude=lng_val,
            created_by=request.user,
        )


        # Save details
        if record_type == 'Permit':
            PermitDetail.objects.create(
                engineering_record=record,
                permit_type=subtype,
                building_type=request.POST.get('building_type', ''),
                permit_number=permit_number,
                applicant_name=applicant_name,
                remarks=sanitize_input(request.POST.get('remarks', '')).strip(),
            )
        elif record_type == 'Project':
            project_status = request.POST.get('project_status', 'Planning')
            ProjectDetail.objects.create(
                engineering_record=record,
                project_type=subtype,
                funding_source=sanitize_input(request.POST.get('funding_source', '')).strip(),
                contractor=sanitize_input(request.POST.get('contractor', '')).strip(),
                project_cost=parse_decimal_safely(request.POST.get('project_cost')),
                project_status=project_status,
            )
            # Sync parent record status based on project status
            if project_status == 'Completed':
                record.status = 'completed'
            elif project_status == 'Ongoing':
                record.status = 'in_progress'
            else:
                record.status = 'active'
            record.save()

        # Generate Checklist requirements from template
        template = RequirementTemplate.objects.filter(
            record_type=record_type, subtype=subtype, scope=scope, is_active=True
        ).first()
        if template:
            RecordRequirement.objects.bulk_create([
                RecordRequirement(record=record, requirement_item=item)
                for item in template.active_items
            ])

        log_audit(
            request.user,
            f"Created {record_type} record: '{title}'",
            record.record_id, request
        )
        messages.success(request, f"Record '{title}' created successfully! Check list is ready.")
        return redirect('record_detail', record_id=record.record_id)

    return render(request, 'permits/create_record.html', {
        'barangays': barangays,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'current_year': timezone.now().year,
        'active_tab': 'records',
    })




# ─── RECORD DETAIL ───────────────────────────────────────────────────────────

@login_required
def record_detail_view(request, record_id):
    record = get_object_or_404(EngineeringRecord, record_id=record_id)

    # Auto-populate checklist requirements if missing
    # Skip for pure violation reports (no permit_detail = just an incident report, no checklist needed)
    is_pure_violation = record.is_illegal_construction
    try:
        _ = record.permit_detail
    except PermitDetail.DoesNotExist:
        if record.record_type == 'Permit':
            is_pure_violation = True
    
    if not record.requirements.exists() and not is_pure_violation:
        template = None
        if record.record_type == 'Permit':
            subtype = record.permit_detail.permit_type if hasattr(record, 'permit_detail') and record.permit_detail and record.permit_detail.permit_type else 'Building'
            template = RequirementTemplate.objects.filter(record_type='Permit', subtype=subtype, is_active=True).first()
            if not template:
                template = RequirementTemplate.objects.filter(record_type='Permit', subtype='Building', is_active=True).first()
        elif record.record_type == 'Project':
            subtype = record.project_detail.project_type if hasattr(record, 'project_detail') and record.project_detail and record.project_detail.project_type else 'Road & Bridge'
            scope = record.project_scope or 'Municipal'
            template = RequirementTemplate.objects.filter(record_type='Project', subtype=subtype, scope=scope, is_active=True).first()

        if template:
            RecordRequirement.objects.bulk_create([
                RecordRequirement(record=record, requirement_item=item)
                for item in template.active_items
            ])

    # Load checklist requirements with their linked documents
    requirements = record.requirements.select_related(
        'requirement_item', 'document', 'fulfilled_by'
    ).order_by('requirement_item__order', 'requirement_item__name')

    # Completion stats
    completion = record.completion_stats

    # Non-checklist documents (uploaded without a slot)
    documents = record.documents.filter(requirement_item__isnull=True).order_by('-uploaded_at')

    # Generate signed URLs for all documents
    all_docs = record.documents.all()
    doc_url_map = {}
    for doc in all_docs:
        doc_url_map[doc.document_id] = reverse('serve_document', kwargs={
            'token': signing.dumps({'document_id': doc.document_id}, salt='document-download')
        })

    # Get detail
    permit_detail = None
    project_detail = None
    if record.record_type == 'Permit':
        try:
            permit_detail = record.permit_detail
        except PermitDetail.DoesNotExist:
            pass
    elif record.record_type == 'Project':
        try:
            project_detail = record.project_detail
        except (ProjectDetail.DoesNotExist, Exception):
            pass

    # Activity timeline
    timeline = AuditLog.objects.filter(
        target_record_id=record_id
    ).select_related('user').order_by('-performed_at')

    # Related records (same barangay, same type)
    related_records = EngineeringRecord.objects.filter(
        barangay=record.barangay,
        record_type=record.record_type,
    ).exclude(record_id=record.record_id).select_related('barangay')[:4]

    # Auto-ensure child RecordRequirement objects exist for all parent requirement items
    existing_item_ids = set(requirements.values_list('requirement_item_id', flat=True))
    missing_child_items = RequirementItem.objects.filter(
        parent_id__in=existing_item_ids,
        is_active=True
    ).exclude(item_id__in=existing_item_ids)

    if missing_child_items.exists():
        RecordRequirement.objects.bulk_create([
            RecordRequirement(record=record, requirement_item=item)
            for item in missing_child_items
        ])
        requirements = record.requirements.select_related(
            'requirement_item', 'document', 'fulfilled_by'
        ).order_by('requirement_item__order', 'requirement_item__name')

    # Build tree hierarchy: parent requirements -> sub requirements
    parent_reqs = []
    sub_reqs_by_parent = {}
    
    for req in requirements:
        if req.requirement_item.parent_id:
            parent_id = req.requirement_item.parent_id
            if parent_id not in sub_reqs_by_parent:
                sub_reqs_by_parent[parent_id] = []
            sub_reqs_by_parent[parent_id].append(req)
        else:
            parent_reqs.append(req)

    import datetime
    today = timezone.now().date()
    thirty_days_later = today + datetime.timedelta(days=30)

    context = {
        'record': record,
        'requirements': requirements,
        'parent_reqs': parent_reqs,
        'sub_reqs_by_parent': sub_reqs_by_parent,
        'completion': completion,
        'documents': documents,
        'doc_url_map': doc_url_map,
        'permit_detail': permit_detail,
        'project_detail': project_detail,
        'timeline': timeline,
        'related_records': related_records,
        'can_edit': (request.user.role == 'admin' or (request.user.role == 'staff' and record.created_by == request.user)),
        'can_archive': (request.user.role == 'admin'),
        'active_tab': 'illegal' if (record.is_illegal_construction and record.illegal_compliance_status == 'unresolved') else 'records',
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'today': today,
        'thirty_days_later': thirty_days_later,
    }
    return render(request, 'permits/record_detail.html', context)


@login_required
def record_requirement_detail_view(request, record_id, req_id):
    """Dedicated workspace page for managing a specific requirement category or folder."""
    record = get_object_or_404(EngineeringRecord, pk=record_id)
    req = get_object_or_404(RecordRequirement.objects.select_related('requirement_item', 'document'), pk=req_id, record=record)

    # Find all sub-items under this requirement_item
    sub_item_qs = RequirementItem.objects.filter(parent=req.requirement_item, is_active=True).order_by('order', 'name')
    
    # Get or create RecordRequirements for these sub-items
    sub_reqs = []
    if sub_item_qs.exists():
        existing_sub_reqs = {
            sr.requirement_item_id: sr 
            for sr in RecordRequirement.objects.filter(record=record, requirement_item__in=sub_item_qs).select_related('requirement_item', 'document', 'fulfilled_by')
        }
        
        missing_items = [item for item in sub_item_qs if item.item_id not in existing_sub_reqs]
        if missing_items:
            RecordRequirement.objects.bulk_create([
                RecordRequirement(record=record, requirement_item=item)
                for item in missing_items
            ])
            existing_sub_reqs = {
                sr.requirement_item_id: sr 
                for sr in RecordRequirement.objects.filter(record=record, requirement_item__in=sub_item_qs).select_related('requirement_item', 'document', 'fulfilled_by')
            }

        sub_reqs = [existing_sub_reqs[item.item_id] for item in sub_item_qs if item.item_id in existing_sub_reqs]

    # Generate document signed URLs
    all_docs = record.documents.all()
    doc_url_map = {}
    for doc in all_docs:
        doc_url_map[doc.document_id] = reverse('serve_document', kwargs={
            'token': signing.dumps({'document_id': doc.document_id}, salt='document-download')
        })

    can_edit = (request.user.role == 'admin' or (request.user.role == 'staff' and record.created_by == request.user))

    # Stats
    total_sub = len(sub_reqs) if sub_reqs else 1
    fulfilled_sub = sum(1 for s in sub_reqs if s.is_fulfilled) if sub_reqs else (1 if req.is_fulfilled else 0)

    context = {
        'record': record,
        'req': req,
        'sub_reqs': sub_reqs,
        'total_sub': total_sub,
        'fulfilled_sub': fulfilled_sub,
        'doc_url_map': doc_url_map,
        'can_edit': can_edit,
        'active_tab': 'records',
    }
    return render(request, 'permits/record_requirement_detail.html', context)


@login_required
def update_illegal_status_view(request, record_id):
    """Updates illegal construction status / compliance regularization status for a record."""
    if request.user.role not in ['staff', 'admin']:
        return HttpResponseForbidden("Unauthorized")
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if request.method == 'POST':
        status_val = request.POST.get('illegal_compliance_status', '').strip()
        flag_val = request.POST.get('is_illegal_construction', '')
        
        if flag_val == 'toggle':
            record.is_illegal_construction = not record.is_illegal_construction
            if record.is_illegal_construction and not record.illegal_compliance_status:
                record.illegal_compliance_status = 'unresolved'
            record.save()
            action_msg = "Flagged as Illegal Construction." if record.is_illegal_construction else "Unflagged Illegal Construction."
            log_audit(request.user, action_msg, target_record_id=record.record_id, request=request)
            messages.success(request, action_msg)
        elif status_val in ['unresolved', 'pending_permit']:
            record.is_illegal_construction = True
            record.illegal_compliance_status = status_val
            record.save()
            lbl = record.get_illegal_compliance_status_display()
            log_audit(request.user, f"Updated Illegal Construction Compliance to {lbl}", target_record_id=record.record_id, request=request)
            messages.success(request, f"Regularization status updated to '{lbl}'.")
        elif status_val == 'remove':
            record.is_illegal_construction = False
            record.save()
            log_audit(request.user, "Removed Illegal Construction flag", target_record_id=record.record_id, request=request)
            messages.success(request, "Illegal construction flag removed.")
            
    return redirect('record_detail', record_id=record.record_id)


@login_required
def regularize_record_view(request, record_id):
    """
    Converts a compliant unpermitted construction incident into an official regularized permit record.
    Staff specifies the exact Permit Type (e.g. Building Permit, Fencing Permit, etc.), Permit Number, and Applicant Name.
    """
    if request.user.role not in ['staff', 'admin']:
        return HttpResponseForbidden("Unauthorized")

    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if request.method == 'POST':
        permit_type = sanitize_input(request.POST.get('permit_type', 'Building Permit')).strip()
        permit_number = sanitize_input(request.POST.get('permit_number', '')).strip()
        applicant_name = sanitize_input(request.POST.get('applicant_name', '')).strip()
        building_type = sanitize_input(request.POST.get('building_type', 'Residential')).strip()

        # Update or create PermitDetail
        permit_detail, created = PermitDetail.objects.get_or_create(engineering_record=record)
        permit_detail.permit_type = permit_type
        if permit_number:
            permit_detail.permit_number = permit_number
        if applicant_name:
            permit_detail.applicant_name = applicant_name
        if building_type:
            permit_detail.building_type = building_type
        permit_detail.save()

        # Update EngineeringRecord
        record.record_type = 'Permit'
        record.is_illegal_construction = True
        record.illegal_compliance_status = 'resolved'
        record.save()

        log_audit(
            request.user,
            f"Regularized incident case into {permit_type} (Permit #{permit_detail.permit_number or 'N/A'})",
            target_record_id=record.record_id,
            request=request
        )
        messages.success(
            request,
            f"Successfully regularized case into official {permit_type}! Record is now available in Master Records."
        )

    return redirect('record_detail', record_id=record.record_id)


@login_required
def flag_illegal_construction_view(request):
    """Creates a simple violation/incident report record — no checklist, no permit detail.
    Checklist is only attached if/when the owner applies for a retroactive building permit."""
    if request.user.role not in ['staff', 'admin']:
        return HttpResponseForbidden("Unauthorized")
    
    if request.method == 'POST':
        title = sanitize_input(request.POST.get('title', '')).strip()
        barangay_id = request.POST.get('barangay', '')
        location_address = sanitize_input(request.POST.get('location_address', '')).strip()
        violation_type = sanitize_input(request.POST.get('violation_type', 'Unpermitted Construction')).strip()
        structure_type = sanitize_input(request.POST.get('structure_type', 'Residential')).strip()
        action_taken = sanitize_input(request.POST.get('action_taken', 'Notice of Violation / Stop Order Issued')).strip()
        description = sanitize_input(request.POST.get('description', '')).strip()
        date_discovered_str = request.POST.get('date_discovered', '')
        remarks = sanitize_input(request.POST.get('remarks', '')).strip()
        owner_name = sanitize_input(request.POST.get('owner_name', '')).strip()
        
        if not title:
            title = "Unpermitted Structure Discovered"
        if not barangay_id:
            messages.error(request, "Please select a barangay.")
            return redirect(request.META.get('HTTP_REFERER', 'records_browse'))
            
        barangay = get_object_or_404(Barangay, barangay_id=barangay_id)
        
        # Parse date discovered or default to today
        if date_discovered_str:
            try:
                from datetime import datetime
                date_discovered = datetime.strptime(date_discovered_str, '%Y-%m-%d').date()
            except ValueError:
                date_discovered = timezone.now().date()
        else:
            date_discovered = timezone.now().date()
        
        # Build a clear, structured description matching official LGU inspection forms
        desc_parts = []
        if violation_type:
            desc_parts.append(f"Violation Category: {violation_type}")
        if structure_type:
            desc_parts.append(f"Structure Type: {structure_type}")
        if location_address:
            desc_parts.append(f"Location: {location_address}")
        if action_taken:
            desc_parts.append(f"Enforcement Action: {action_taken}")
        if description:
            desc_parts.append(f"Inspection Findings: {description}")
        if remarks:
            desc_parts.append(f"Remarks: {remarks}")
        full_description = '\n'.join(desc_parts) if desc_parts else title
        
        record = EngineeringRecord.objects.create(
            record_type='Permit',
            project_scope='',
            barangay=barangay,
            title=title,
            year=date_discovered.year,
            description=full_description,
            status='active',
            date_started=date_discovered,
            is_illegal_construction=True,
            illegal_compliance_status='unresolved',
            created_by=request.user
        )
        
        # Store in PermitDetail for applicant/violator tracking & structure categorization
        PermitDetail.objects.create(
            engineering_record=record,
            permit_type='Violation Report',
            applicant_name=owner_name if owner_name else 'Under Investigation',
            building_type=structure_type if structure_type else 'Residential'
        )

        # Handle photo/document upload (Digital Evidence Storage)
        if 'photo' in request.FILES and request.FILES['photo']:
            photo_file = request.FILES['photo']
            try:
                from django.core.exceptions import ValidationError
                validate_document_file(photo_file)
                Document.objects.create(
                    engineering_record=record,
                    document_type='Picture',
                    file_name=photo_file.name,
                    file=photo_file,
                    file_size=photo_file.size,
                    uploaded_by=request.user
                )
            except ValidationError as err:
                messages.warning(request, f"Report created, but file upload failed: {str(err)}")
                
        log_audit(
            request.user,
            f"Reported violation at Brgy. {barangay.barangay_name}: '{title}' — {violation_type}",
            target_record_id=record.record_id,
            request=request
        )
        messages.success(request, f"Violation report created for Brgy. {barangay.barangay_name}.")
        return redirect('record_detail', record_id=record.record_id)

    return redirect('records_browse')



@login_required
def toggle_requirement_waived_view(request, req_id):
    """Toggles the waived (N/A) status of a specific record requirement."""
    if request.user.role not in ['staff', 'admin']:
        return HttpResponseForbidden("Unauthorized")
        
    req = get_object_or_404(RecordRequirement, req_id=req_id)
    
    # Permission check: staff can only toggle requirements for records they created
    if request.user.role == 'staff' and req.record.created_by != request.user:
        return HttpResponseForbidden("You can only edit requirements for records you created.")
    
    req.is_waived = not req.is_waived
    req.save()
    
    action_str = "marked as N/A" if req.is_waived else "marked as required"
    messages.success(request, f"Requirement '{req.requirement_item.name}' successfully {action_str}.")
    log_audit(
        request.user, 
        f"Requirement '{req.requirement_item.name}' {action_str} for record '{req.record.title}'", 
        target_record_id=req.record.record_id, 
        request=request
    )
    
    stats = req.record.completion_stats
    return JsonResponse({
        'success': True,
        'is_waived': req.is_waived,
        'fulfilled': stats['fulfilled'],
        'total': stats['total'],
        'pct': stats['pct'],
        'is_complete': stats['is_complete']
    })


# ─── RECORD EDIT ─────────────────────────────────────────────────────────────

@login_required
def record_edit_view(request, record_id):
    record = get_object_or_404(EngineeringRecord, record_id=record_id)

    # Permission check
    if request.user.role == 'staff' and record.created_by != request.user:
        raise PermissionDenied("You can only edit your own records.")
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to edit records.")

    barangays = Barangay.objects.all()

    if request.method == 'POST':
        record.title = sanitize_input(request.POST.get('title', '')).strip()
        record.description = sanitize_input(request.POST.get('description', '')).strip()
        record.status = request.POST.get('status', record.status)
        record.barangay_id = request.POST.get('barangay', record.barangay_id)
        record.date_started = request.POST.get('date_started', '') or None
        record.date_completed = request.POST.get('date_completed', '') or None
        
        lat_raw = request.POST.get('latitude', '').strip()
        lng_raw = request.POST.get('longitude', '').strip()
        record.latitude = float(lat_raw) if lat_raw else None
        record.longitude = float(lng_raw) if lng_raw else None

        # Preserve illegal construction status unless explicitly passed in POST
        if 'is_illegal_construction' in request.POST:
            is_illegal = request.POST.get('is_illegal_construction') in ['on', 'true', '1']
            record.is_illegal_construction = is_illegal
            if is_illegal:
                record.illegal_compliance_status = request.POST.get('illegal_compliance_status', record.illegal_compliance_status or 'unresolved')
            else:
                record.illegal_compliance_status = 'unresolved'
        elif 'illegal_compliance_status' in request.POST and record.is_illegal_construction:
            record.illegal_compliance_status = request.POST.get('illegal_compliance_status', record.illegal_compliance_status or 'unresolved')
            
        record.save()


        # Update detail and regenerate requirements if subtype changed or doesn't exist
        if record.record_type == 'Permit':
            # Check if this is a pure violation report (no permit_detail)
            try:
                detail = record.permit_detail
            except PermitDetail.DoesNotExist:
                detail = None
            
            if detail:
                # Normal permit record — update detail fields
                applicant_name_val = sanitize_input(request.POST.get('applicant_name', '')).strip()
                if not applicant_name_val:
                    messages.error(request, "Applicant / Property Owner name is required for permits.")
                    return redirect('edit_record', record_id=record.record_id)
                old_subtype = detail.permit_type
                new_subtype = request.POST.get('permit_type', '') or old_subtype
                
                detail.permit_type = new_subtype
                detail.building_type = request.POST.get('building_type', detail.building_type)
                detail.permit_number = sanitize_input(request.POST.get('permit_number', '')).strip()
                detail.applicant_name = applicant_name_val
                detail.resolution_required = request.POST.get('resolution_required') == 'on'
                detail.remarks = sanitize_input(request.POST.get('remarks', '')).strip()
                detail.save()
                
                # Auto-sync record.title with updated permit_number / applicant_name
                if detail.permit_number and detail.applicant_name:
                    record.title = f"{detail.permit_number} — {detail.applicant_name}"
                elif detail.applicant_name:
                    record.title = detail.applicant_name
                elif detail.permit_number:
                    record.title = detail.permit_number
                record.save()
                
                if not record.requirements.exists() or old_subtype != new_subtype:
                    record.requirements.all().delete()
                    template = RequirementTemplate.objects.filter(
                        record_type='Permit', subtype=new_subtype, is_active=True
                    ).first()
                    if template:
                        RecordRequirement.objects.bulk_create([
                            RecordRequirement(record=record, requirement_item=item)
                            for item in template.active_items
                        ])
            # else: pure violation report — only basic fields (title, description, barangay) were updated above
                    
        elif record.record_type == 'Project':
            contractor_val = sanitize_input(request.POST.get('contractor', '')).strip()
            if not contractor_val:
                messages.error(request, "Contractor or Implementing Entity is required for projects (or specify 'By Administration').")
                return redirect('edit_record', record_id=record.record_id)
            detail, _ = ProjectDetail.objects.get_or_create(engineering_record=record)
            old_subtype = detail.project_type
            new_subtype = request.POST.get('project_type', '')
            
            detail.project_type = new_subtype
            detail.funding_source = sanitize_input(request.POST.get('funding_source', '')).strip()
            detail.contractor = contractor_val
            detail.project_cost = parse_decimal_safely(request.POST.get('project_cost'))
            project_status = request.POST.get('project_status', detail.project_status)
            detail.project_status = project_status
            detail.save()
            
            # Sync parent record status based on project status
            if project_status == 'Completed':
                record.status = 'completed'
            elif project_status == 'Ongoing':
                record.status = 'in_progress'
            else:
                if record.status not in ['archived', 'pending']:
                    record.status = 'active'
            record.save()
            
            if not record.requirements.exists() or old_subtype != new_subtype:
                record.requirements.all().delete()
                template = RequirementTemplate.objects.filter(
                    record_type='Project', subtype=new_subtype, scope=record.project_scope, is_active=True
                ).first()
                if template:
                    RecordRequirement.objects.bulk_create([
                        RecordRequirement(record=record, requirement_item=item)
                        for item in template.active_items
                    ])

        log_audit(request.user, f"Updated {record.record_type}: '{record.title}'", record.record_id, request)
        messages.success(request, f"Record '{record.title}' updated successfully.")
        return redirect('record_detail', record_id=record.record_id)

    # Get detail for form
    permit_detail = None
    project_detail = None
    if record.record_type == 'Permit':
        try:
            permit_detail = record.permit_detail
        except PermitDetail.DoesNotExist:
            pass
    elif record.record_type == 'Project':
        try:
            project_detail = record.project_detail
        except ProjectDetail.DoesNotExist:
            pass

    context = {
        'record': record,
        'permit_detail': permit_detail,
        'project_detail': project_detail,
        'barangays': barangays,
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'project_types': ProjectDetail.PROJECT_TYPE_CHOICES,
        'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
        'funding_sources': ProjectDetail.FUNDING_SOURCE_CHOICES,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'active_tab': 'records',
    }
    return render(request, 'permits/edit_record.html', context)


# ─── SERVE SECURE DOCUMENT ──────────────────────────────────────────────────

def _get_document_stream(doc):
    """
    Robustly resolves a Document file object across local storage, subdirectories,
    Supabase Storage, and in-memory fallbacks. Prevents [Errno 2] No such file errors.
    """
    import mimetypes
    import io
    from django.conf import settings

    file_name = doc.file_name or (doc.file.name if doc.file else 'document')
    fn_lower = file_name.lower()
    content_type, _ = mimetypes.guess_type(file_name)
    if not content_type:
        if fn_lower.endswith('.pdf'):
            content_type = 'application/pdf'
        elif fn_lower.endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif fn_lower.endswith('.png'):
            content_type = 'image/png'
        elif fn_lower.endswith('.webp'):
            content_type = 'image/webp'
        else:
            content_type = 'application/octet-stream'

    raw_name = str(doc.file.name) if doc.file else ''
    clean_name = raw_name.replace('media/', '').replace('media\\', '').lstrip('/\\')
    base_name = os.path.basename(clean_name)

    candidates = [
        os.path.join(settings.MEDIA_ROOT, clean_name),
        os.path.join(settings.MEDIA_ROOT, raw_name),
        os.path.join(settings.MEDIA_ROOT, 'documents', base_name),
        os.path.join(settings.MEDIA_ROOT, 'temp_uploads', base_name),
        os.path.join(settings.MEDIA_ROOT, base_name),
    ]

    try:
        if hasattr(doc.file, 'path') and doc.file.path:
            candidates.insert(0, doc.file.path)
    except Exception:
        pass

    for path in candidates:
        if path and os.path.exists(path) and os.path.isfile(path):
            try:
                f = open(path, 'rb')
                return f, content_type, None
            except Exception as e:
                logger.warning(f"Failed opening candidate path {path}: {e}")

    # Try standard storage open
    if doc.file:
        try:
            f = doc.file.open('rb')
            return f, content_type, None
        except Exception:
            pass

    # Check Supabase / remote URL
    try:
        url = doc.file.url
        if url and str(url).startswith(('http://', 'https://')):
            return None, content_type, url
    except Exception:
        pass

    # In-memory fallback if sample/seed file is missing on local server
    record_title = doc.engineering_record.title if doc.engineering_record else "Engineering Record"
    if content_type == 'application/pdf' or fn_lower.endswith('.pdf'):
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 160 >>
stream
BT
/F1 16 Tf
50 720 Td
(eTala - Municipal Engineering Office) Tj
/F1 12 Tf
0 -30 Td
(Document: {doc.document_type} - {doc.file_name[:45]}) Tj
0 -20 Td
(Record: {record_title[:50]}) Tj
0 -20 Td
(Status: Digitized Archive Reference) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000059 00000 n 
0000000116 00000 n 
0000000227 00000 n 
0000000438 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
508
%%EOF"""
        return io.BytesIO(pdf_content.encode('latin-1')), 'application/pdf', None

    # Fallback 1x1 transparent PNG for images
    png_bytes = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
        b'\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf'
        b'\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return io.BytesIO(png_bytes), content_type or 'image/png', None


@login_required
def serve_document_view(request, token):
    doc = None
    if str(token).isdigit():
        doc = get_object_or_404(Document, document_id=int(token))
    else:
        try:
            data = signing.loads(token, salt='document-download')
            doc = get_object_or_404(Document, document_id=data['document_id'])
        except (signing.SignatureExpired, signing.BadSignature):
            try:
                doc = get_object_or_404(Document, document_id=token)
            except Exception:
                return HttpResponseForbidden("Invalid document token link.")

    if not doc:
        raise Http404("Document not found.")

    # Authorization Check: Authenticated LGU staff, engineers, and admins can view documents on active records. Non-admin users cannot access archived record documents.
    if doc.engineering_record:
        rec = doc.engineering_record
        if rec.status == 'archived' and request.user.role != 'admin':
            return HttpResponseForbidden("You do not have permission to view documents for archived records.")

    file_obj, content_type, redirect_url = _get_document_stream(doc)
    if redirect_url:
        return redirect(redirect_url)

    file_name = doc.file_name or (doc.file.name if doc.file else 'document')
    safe_filename = os.path.basename(file_name).replace('"', '')
    response = FileResponse(file_obj, content_type=content_type)
    response['Content-Disposition'] = f'inline; filename="{safe_filename}"'
    return response


# ─── DOCUMENT UPLOAD / DELETE ────────────────────────────────────────────────

@login_required
def document_upload_view(request, record_id):
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'json' in request.headers.get('Accept', '').lower()

    if request.user.role not in ['staff', 'admin']:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'You do not have permission to upload documents.'}, status=403)
        raise PermissionDenied("You do not have permission to upload documents.")

    if request.method == 'POST':
        document_file = request.FILES.get('document_file')
        requirement_item_id = request.POST.get('requirement_item_id', '').strip()
        document_type = request.POST.get('document_type', 'Other').strip()
        expiry_date = request.POST.get('expiry_date', '').strip()

        if not document_file:
            err_msg = "Please select a file to upload."
            if is_ajax:
                return JsonResponse({'success': False, 'error': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('record_detail', record_id=record.record_id)

        try:
            validate_document_file(document_file)
        except Exception as exc:
            err_msg = exc.message if hasattr(exc, 'message') else str(exc)
            if is_ajax:
                return JsonResponse({'success': False, 'error': err_msg}, status=400)
            messages.error(request, err_msg)
            return redirect('record_detail', record_id=record.record_id)

        import datetime
        parsed_expiry_date = None
        if expiry_date:
            try:
                parsed_expiry_date = datetime.datetime.strptime(expiry_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        new_version = 1
        req_item = None
        if requirement_item_id:
            try:
                req_item = RequirementItem.objects.get(item_id=requirement_item_id)
                document_type = req_item.name[:50]  # truncate to 50 chars max for Document model CharField
                # Prevent orphan file/record leaks by checking for existing documents in this slot
                existing_req = RecordRequirement.objects.filter(record=record, requirement_item=req_item).first()
                if existing_req and existing_req.document:
                    old_doc = existing_req.document
                    new_version = (old_doc.version or 1) + 1
                    try:
                        old_doc.file.delete()
                        old_doc.delete()
                    except Exception as e:
                        logger.error(f"Error deleting replaced document: {e}")
            except RequirementItem.DoesNotExist:
                pass

        try:
            doc = Document.objects.create(
                engineering_record=record,
                requirement_item=req_item,
                document_type=document_type,
                file=document_file,
                file_name=document_file.name,
                file_size=document_file.size,
                version=new_version,
                uploaded_by=request.user,
                expiry_date=parsed_expiry_date,
            )
        except Exception as exc:
            logger.warning(f"Supabase storage save failed for document upload: {exc}. Trying local FileSystemStorage fallback.")
            try:
                from django.core.files.storage import FileSystemStorage
                fs = FileSystemStorage()
                if hasattr(document_file, 'seek'):
                    try:
                        document_file.seek(0)
                    except Exception:
                        pass
                saved_path = fs.save(f"documents/{document_file.name}", document_file)
                doc = Document.objects.create(
                    engineering_record=record,
                    requirement_item=req_item,
                    document_type=document_type,
                    file=saved_path,
                    file_name=document_file.name,
                    file_size=document_file.size,
                    uploaded_by=request.user,
                    expiry_date=parsed_expiry_date,
                )
            except Exception as fallback_exc:
                logger.error(f"Failed saving document file to storage: {fallback_exc}")
                err_msg = f"Storage Save Error: {str(fallback_exc)}"
                if is_ajax:
                    return JsonResponse({'success': False, 'error': err_msg}, status=500)
                messages.error(request, err_msg)
                return redirect('record_detail', record_id=record.record_id)

        # Mark the corresponding checklist slot as fulfilled
        if req_item:
            RecordRequirement.objects.filter(
                record=record, requirement_item=req_item
            ).update(
                document=doc,
                is_fulfilled=True,
                fulfilled_at=timezone.now(),
                fulfilled_by=request.user,
            )

        log_audit(
            request.user,
            f"Uploaded: {req_item.name if req_item else 'general'} for '{record.title}'",
            record.record_id, request
        )
        msg_str = f"Uploaded: {req_item.name if req_item else 'general'} successfully."
        messages.success(request, msg_str)

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': msg_str,
                'doc_id': doc.document_id,
                'file_name': doc.file_name,
                'file_url': f"/documents/serve/{doc.document_id}/"
            })

    return redirect('record_detail', record_id=record.record_id)


@login_required
def document_delete_view(request, record_id, document_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    doc = get_object_or_404(Document, document_id=document_id, engineering_record=record)

    if request.user.role != 'admin':
        raise PermissionDenied("Only Administrators can delete documents.")

    # Mark the corresponding checklist requirement slot as unfulfilled
    RecordRequirement.objects.filter(document=doc).update(
        document=None,
        is_fulfilled=False,
        fulfilled_at=None,
        fulfilled_by=None
    )

    doc.file.delete()
    doc.delete()
    doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
    log_audit(request.user, f"Deleted: {doc_label} from '{record.title}'", record.record_id, request)
    messages.success(request, f"Deleted: {doc_label} successfully.")
    return redirect('record_detail', record_id=record.record_id)


# (download_record_zip_view defined below under ZIP DOWNLOAD section)


# ─── ARCHIVE / RESTORE ──────────────────────────────────────────────────────

@login_required
def record_archive_view(request, record_id):
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if request.user.role != 'admin':
        raise PermissionDenied("Only Administrators can archive records.")

    record.status = 'archived'
    record.save()
    log_audit(request.user, f"Archived: '{record.title}'", record.record_id, request)
    messages.success(request, f"Record '{record.title}' archived.")
    return redirect('records_browse')


@login_required
def record_restore_view(request, record_id):
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if request.user.role != 'admin':
        raise PermissionDenied("Only Administrators can restore records.")

    record.status = 'active'
    record.save()
    log_audit(request.user, f"Restored: '{record.title}'", record.record_id, request)
    messages.success(request, f"Record '{record.title}' restored.")
    return redirect('record_detail', record_id=record.record_id)


# ─── ARCHIVE PAGE ───────────────────────────────────────────────────────────

@login_required
def archive_view(request):
    if request.user.role != 'admin':
        raise PermissionDenied("Only Administrators can view archived records.")
    records = EngineeringRecord.objects.filter(status='archived').select_related('barangay', 'created_by')

    query = request.GET.get('q', '').strip()
    if query:
        records = records.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'per_page': per_page,
        'page_obj': page_obj,
        'q': query,
        'active_tab': 'archive',
    }
    return render(request, 'permits/archive.html', context)


# ─── SEARCH ──────────────────────────────────────────────────────────────────

@login_required
def search_view(request):
    query = request.GET.get('q', '').strip()
    record_type = request.GET.get('record_type', '').strip()
    barangay_id = request.GET.get('barangay', '').strip()
    year = request.GET.get('year', '').strip()
    status = request.GET.get('status', '').strip()

    records = EngineeringRecord.objects.exclude(status='archived').select_related(
        'barangay', 'created_by', 'permit_detail', 'project_detail'
    ).prefetch_related(
        'documents', 'requirements__requirement_item', 'requirements__document'
    )

    # Filter by query search
    records = filter_engineering_records(records, query=query)

    # Calculate tab counts BEFORE applying record_type filter to preserve query total tab counts
    base_counts_records = records
    all_count = base_counts_records.count()
    municipal_count = base_counts_records.filter(record_type='Project', project_scope='Municipal').count()
    barangay_count = base_counts_records.filter(record_type='Project', project_scope='Barangay').count()
    permits_count = base_counts_records.filter(record_type='Permit').count()
    illegal_count = base_counts_records.filter(is_illegal_construction=True).count()

    # Apply remaining dropdown filters
    records = filter_engineering_records(records, record_type=record_type, barangay_id=barangay_id, year=year, status=status)

    per_page = get_per_page(request, 10)
    paginator = Paginator(records, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    barangays = Barangay.objects.all().order_by('barangay_name')

    context = {
        'page_obj': page_obj,
        'q': query,
        'all_count': all_count,
        'municipal_count': municipal_count,
        'barangay_count': barangay_count,
        'permits_count': permits_count,
        'illegal_count': illegal_count,
        'selected_record_type': record_type,
        'selected_barangay': barangay_id,
        'selected_year': year,
        'selected_status': status,
        'barangays': barangays,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'year_choices': get_year_choices(),
        'active_tab': 'search',
        'per_page': per_page,
    }
    return render(request, 'permits/search.html', context)




# ─── REPORTS ─────────────────────────────────────────────────────────────────

@login_required
def reports_view(request):
    """Generates detailed statistics and groupings for engineering records."""
    if request.user.role not in ['admin', 'staff']:
        raise PermissionDenied("Only authorized staff and Administrators can view summary reports.")

    # 1. Get filter parameters
    selected_record_type = request.GET.get('record_type', '').strip()
    selected_barangay = request.GET.get('barangay', '').strip()
    selected_year = request.GET.get('year', '').strip()
    selected_status = request.GET.get('status', '').strip()

    # 2. Start with all records ordered chronologically (oldest / earliest records first)
    records = EngineeringRecord.objects.all().select_related(
        'barangay', 'permit_detail', 'project_detail', 'created_by'
    ).prefetch_related(
        'requirements__requirement_item', 'requirements__document'
    ).order_by('record_id')

    # Apply filters to base queryset
    if selected_record_type:
        records = records.filter(record_type=selected_record_type)
    if selected_barangay:
        records = records.filter(barangay_id=selected_barangay)
    if selected_year:
        records = records.filter(year=selected_year)
    if selected_status:
        records = records.filter(status=selected_status)

    # Intercept for exports
    export_format = request.GET.get('export', '').strip().lower()
    if export_format in ['excel', 'pdf']:
        # Format filters description
        meta_info = []
        if selected_record_type:
            meta_info.append(f"Category: {selected_record_type}s")
        if selected_barangay:
            barangay_obj = Barangay.objects.filter(barangay_id=selected_barangay).first()
            if barangay_obj:
                meta_info.append(f"Barangay: {barangay_obj.barangay_name}")
        if selected_year:
            meta_info.append(f"Year: {selected_year}")
        if selected_status:
            status_lbl = dict(EngineeringRecord.STATUS_CHOICES).get(selected_status, selected_status)
            meta_info.append(f"Status: {status_lbl}")

        active_filter_str = ", ".join(meta_info) if meta_info else "All Engineering Records"
        gen_timestamp = timezone.now().strftime("%B %d, %Y • %I:%M %p")

        if export_format == 'excel':
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from django.http import HttpResponse

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Engineering Records"
            ws.views.sheetView[0].showGridLines = True

            # Color Palette
            NAVY_HEX = '002855'
            GOLD_HEX = 'C5A059'
            SLATE_LIGHT = 'F8FAFC'
            BORDER_GRAY = 'CBD5E1'

            # Violation Highlight Tints (Excel)
            RED_BG_HEX = 'FEE2E2'
            RED_TEXT_HEX = 'B91C1C'
            AMBER_BG_HEX = 'FEF3C7'
            AMBER_TEXT_HEX = 'B45309'
            GREEN_BG_HEX = 'DCFCE7'
            GREEN_TEXT_HEX = '15803D'

            title_sub_font = Font(name='Segoe UI', size=9, bold=True, color='475569')
            title_main_font = Font(name='Segoe UI', size=13, bold=True, color=NAVY_HEX)
            title_report_font = Font(name='Segoe UI', size=11, bold=True, color=GOLD_HEX)
            meta_font = Font(name='Segoe UI', size=8.5, italic=True, color='64748B')
            header_font = Font(name='Segoe UI', size=9.5, bold=True, color='FFFFFF')
            data_font = Font(name='Segoe UI', size=9)
            total_font = Font(name='Segoe UI', size=9.5, bold=True, color=NAVY_HEX)
            
            header_fill = PatternFill(start_color=NAVY_HEX, end_color=NAVY_HEX, fill_type='solid')
            alt_row_fill = PatternFill(start_color=SLATE_LIGHT, end_color=SLATE_LIGHT, fill_type='solid')
            total_fill = PatternFill(start_color='EEF2F6', end_color='EEF2F6', fill_type='solid')

            violation_unresolved_fill = PatternFill(start_color=RED_BG_HEX, end_color=RED_BG_HEX, fill_type='solid')
            violation_unresolved_font = Font(name='Segoe UI', size=9, bold=True, color=RED_TEXT_HEX)
            
            violation_pending_fill = PatternFill(start_color=AMBER_BG_HEX, end_color=AMBER_BG_HEX, fill_type='solid')
            violation_pending_font = Font(name='Segoe UI', size=9, bold=True, color=AMBER_TEXT_HEX)
            
            violation_resolved_fill = PatternFill(start_color=GREEN_BG_HEX, end_color=GREEN_BG_HEX, fill_type='solid')
            violation_resolved_font = Font(name='Segoe UI', size=9, bold=True, color=GREEN_TEXT_HEX)

            thin_border = Border(
                left=Side(style='thin', color=BORDER_GRAY),
                right=Side(style='thin', color=BORDER_GRAY),
                top=Side(style='thin', color=BORDER_GRAY),
                bottom=Side(style='thin', color=BORDER_GRAY)
            )
            double_bottom_border = Border(
                left=Side(style='thin', color=BORDER_GRAY),
                right=Side(style='thin', color=BORDER_GRAY),
                top=Side(style='thin', color='94A3B8'),
                bottom=Side(style='double', color=NAVY_HEX)
            )

            # Title Header Block
            ws['A1'] = "REPUBLIC OF THE PHILIPPINES • PROVINCE OF LEYTE"
            ws['A1'].font = title_sub_font
            ws['A2'] = "MUNICIPALITY OF CARIGARA • OFFICE OF THE MUNICIPAL ENGINEER"
            ws['A2'].font = title_main_font
            ws['A3'] = "Engineering Records Summary Report"
            ws['A3'].font = title_report_font
            ws['A4'] = f"Generated: {gen_timestamp}  |  Filters: {active_filter_str}  |  Total: {records.count()} records"
            ws['A4'].font = meta_font

            ws.append([]) # Row 5 empty

            headers = ["Record ID", "Record Title", "Type", "Barangay", "Year", "Status", "Applicant", "Contractor", "Cost / Budget (₱)", "Uploads"]
            ws.append(headers)
            header_row_idx = 6

            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=header_row_idx, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center' if col_idx in [1, 3, 5, 6, 10] else ('right' if col_idx == 9 else 'left'), vertical='center')
                cell.border = thin_border
            ws.row_dimensions[header_row_idx].height = 24

            total_val = 0
            for idx, r in enumerate(records, 1):
                is_violation = bool(r.is_illegal_construction)
                violation_status = r.illegal_compliance_status or 'unresolved'

                if is_violation:
                    if violation_status == 'unresolved':
                        status_label = "Unresolved"
                        row_fill = violation_unresolved_fill
                        row_highlight_font = violation_unresolved_font
                    elif violation_status == 'pending_permit':
                        status_label = "Permit Filed"
                        row_fill = violation_pending_fill
                        row_highlight_font = violation_pending_font
                    elif violation_status == 'resolved':
                        status_label = "Regularized"
                        row_fill = violation_resolved_fill
                        row_highlight_font = violation_resolved_font
                    else:
                        status_label = "Violation"
                        row_fill = violation_unresolved_fill
                        row_highlight_font = violation_unresolved_font
                else:
                    status_label = dict(EngineeringRecord.STATUS_CHOICES).get(r.status, r.status)
                    row_fill = alt_row_fill if (idx % 2 == 0) else None
                    row_highlight_font = None
                
                # Resolve Record Title cleanly
                if r.record_type == 'Permit':
                    permit_num = (r.permit_detail.permit_number.strip() if hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.permit_number else '').strip()
                    if permit_num:
                        ref_no = permit_num
                    elif r.title and r.title.strip() and r.title.strip() != '—' and not r.is_illegal_construction and r.title.strip().lower() != 'permit':
                        ref_no = r.title.strip()
                    elif r.is_illegal_construction:
                        ref_no = f"Violation #{r.record_id}"
                    else:
                        ref_no = f"Permit #{r.record_id}"
                else:
                    ref_no = r.title.strip() if r.title and r.title.strip() and r.title.strip() != '—' else f"Project #{r.record_id}"

                # Resolve Specific Type
                if r.record_type == 'Permit':
                    if is_violation:
                        if violation_status == 'resolved':
                            specific_type = "Regularized Building"
                        elif violation_status == 'pending_permit':
                            specific_type = "Violation (Permit Filed)"
                        else:
                            specific_type = "Violation Report"
                    elif hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.permit_type:
                        specific_type = r.specific_type_label
                    else:
                        specific_type = "Building Permit"
                else:
                    if hasattr(r, 'project_detail') and r.project_detail and r.project_detail.project_type:
                        specific_type = r.specific_type_label
                    else:
                        specific_type = f"{r.project_scope} Project" if r.project_scope else "Project"

                # Resolve Applicant and Contractor separately
                applicant_val = "—"
                contractor_val = "—"
                if r.record_type == 'Permit':
                    app_name = (r.permit_detail.applicant_name.strip() if hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.applicant_name else '').strip()
                    if app_name and app_name.lower() not in ['n/a', 'none', 'if applicable', '', '—'] and not app_name.startswith('[') and 'unpermitted' not in app_name.lower() and 'violation' not in app_name.lower():
                        applicant_val = app_name
                else:
                    c_name = (r.project_detail.contractor.strip() if hasattr(r, 'project_detail') and r.project_detail and r.project_detail.contractor else '').strip()
                    if c_name and c_name.lower() not in ['n/a', 'none', 'if applicable', '', '—'] and not c_name.startswith('[') and 'unpermitted' not in c_name.lower() and 'violation' not in c_name.lower():
                        contractor_val = c_name

                # Resolve Cost / Budget
                cost = 0
                if r.record_type == 'Project' and hasattr(r, 'project_detail') and r.project_detail and r.project_detail.project_cost:
                    cost = r.project_detail.project_cost
                    total_val += cost

                # Resolve Upload Completion Status
                c_stats = r.completion_stats
                if c_stats['total'] > 0:
                    doc_status = f"{c_stats['fulfilled']}/{c_stats['total']}"
                else:
                    doc_status = f"{r.documents.count()} files" if is_violation else "—"

                barangay_name = r.barangay.barangay_name if r.barangay else "—"
                year_val = r.year if r.year else "—"

                row_data = [r.record_id, ref_no, specific_type, barangay_name, year_val, status_label, applicant_val, contractor_val, cost if cost > 0 else "—", doc_status]
                ws.append(row_data)
                
                curr_row = ws.max_row
                ws.row_dimensions[curr_row].height = 19

                for col_idx in range(1, len(headers) + 1):
                    cell = ws.cell(row=curr_row, column=col_idx)
                    cell.border = thin_border
                    
                    if is_violation and col_idx in [3, 6]:
                        cell.font = row_highlight_font
                    else:
                        cell.font = data_font

                    if row_fill:
                        cell.fill = row_fill
                    
                    if col_idx in [1, 5, 6, 10]:
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    elif col_idx == 9:
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                        if isinstance(cell.value, (int, float, Decimal)):
                            cell.number_format = '₱#,##0.00'
                    else:
                        cell.alignment = Alignment(horizontal='left', vertical='center')

            # Summary Row
            tot_row_idx = ws.max_row + 1
            ws.row_dimensions[tot_row_idx].height = 22
            ws.cell(row=tot_row_idx, column=1, value="TOTAL").font = total_font
            ws.cell(row=tot_row_idx, column=2, value=f"{records.count()} Record(s)").font = total_font
            ws.cell(row=tot_row_idx, column=8, value="Total Budget:").font = total_font
            
            cost_total_cell = ws.cell(row=tot_row_idx, column=9, value=total_val)
            cost_total_cell.font = total_font
            cost_total_cell.number_format = '₱#,##0.00'
            cost_total_cell.alignment = Alignment(horizontal='right', vertical='center')
            
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=tot_row_idx, column=col_idx)
                cell.border = double_bottom_border
                cell.fill = total_fill
                if col_idx not in [1, 2, 8, 9]:
                    cell.value = ""

            # Auto-fit Column Widths
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col[5:]:
                    if cell.value:
                        val_str = str(cell.value)
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 11)
            ws.column_dimensions['A'].width = 11
            ws.column_dimensions['B'].width = 26
            ws.column_dimensions['C'].width = 20
            ws.column_dimensions['G'].width = 20
            ws.column_dimensions['H'].width = 20
            ws.column_dimensions['I'].width = 18
            ws.column_dimensions['J'].width = 13

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename=eTala_Engineering_Records_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
            wb.save(response)
            return response

        elif export_format == 'pdf':
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            from django.http import HttpResponse
            from django.conf import settings
            import os

            # Register Unicode TTF Font for native Peso Sign (₱) rendering across OS environments
            font_candidates = [
                # Local project assets font
                (os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'DejaVuSans.ttf'), os.path.join(settings.BASE_DIR, 'assets', 'fonts', 'DejaVuSans-Bold.ttf')),
                # Windows system fonts
                (r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\segoeuib.ttf'),
                (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
                # Linux / Container fonts (Debian / Ubuntu / Render)
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
                ('/usr/share/fonts/truetype/freefont/FreeSans.ttf', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
            ]

            font_registered = False
            for reg_path, bold_path in font_candidates:
                try:
                    if os.path.exists(reg_path) and os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont('eTalaFont', reg_path))
                        pdfmetrics.registerFont(TTFont('eTalaFont-Bold', bold_path))
                        font_registered = True
                        break
                except Exception:
                    continue

            main_font = 'eTalaFont' if font_registered else 'Helvetica'
            bold_font = 'eTalaFont-Bold' if font_registered else 'Helvetica-Bold'

            # Running Numbered Canvas with Header & Footer
            class NumberedCanvas(canvas.Canvas):
                def __init__(self, *args, **kwargs):
                    super(NumberedCanvas, self).__init__(*args, **kwargs)
                    self._saved_page_states = []

                def showPage(self):
                    self._saved_page_states.append(dict(self.__dict__))
                    self._startPage()

                def save(self):
                    num_pages = len(self._saved_page_states)
                    for state in self._saved_page_states:
                        self.__dict__.update(state)
                        self.draw_page_decorations(num_pages)
                        canvas.Canvas.showPage(self)
                    canvas.Canvas.save(self)

                def draw_page_decorations(self, page_count):
                    self.saveState()
                    # Running top header on page 2+
                    if self._pageNumber > 1:
                        self.setFont(bold_font, 7.5)
                        self.setFillColor(colors.HexColor("#002855"))
                        self.drawString(36, 582, "MUNICIPAL ENGINEERING OFFICE — CARIGARA, LEYTE")
                        self.setFont(main_font, 7.5)
                        self.setFillColor(colors.HexColor("#64748B"))
                        self.drawRightString(792 - 36, 582, "Engineering Records Summary Report")
                        self.setStrokeColor(colors.HexColor("#CBD5E1"))
                        self.setLineWidth(0.5)
                        self.line(36, 576, 792 - 36, 576)

                    # Running Footer
                    self.setFont(main_font, 7.5)
                    self.setFillColor(colors.HexColor("#64748B"))
                    self.drawString(36, 22, f"Municipal Engineering Office • Carigara, Leyte | eTala Management System | Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
                    self.drawRightString(792 - 36, 22, f"Page {self._pageNumber} of {page_count}")
                    self.setStrokeColor(colors.HexColor("#CBD5E1"))
                    self.setLineWidth(0.5)
                    self.line(36, 32, 792 - 36, 32)
                    self.restoreState()

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(letter),
                rightMargin=36,
                leftMargin=36,
                topMargin=26,
                bottomMargin=40
            )
            
            story = []
            styles = getSampleStyleSheet()

            NAVY = colors.HexColor('#002855')
            GOLD = colors.HexColor('#C5A059')
            TEXT_DARK = colors.HexColor('#0F172A')
            TEXT_MUTED = colors.HexColor('#475569')

            sub_header_style = ParagraphStyle(
                'SubHeaderStyle',
                parent=styles['Normal'],
                fontName=bold_font,
                fontSize=8,
                leading=10,
                textColor=TEXT_MUTED,
                alignment=1
            )
            office_title_style = ParagraphStyle(
                'OfficeTitleStyle',
                parent=styles['Heading1'],
                fontName=bold_font,
                fontSize=12,
                leading=15,
                textColor=NAVY,
                alignment=1
            )
            report_title_style = ParagraphStyle(
                'ReportTitleStyle',
                parent=styles['Heading2'],
                fontName=bold_font,
                fontSize=9.5,
                leading=12,
                textColor=GOLD,
                alignment=1,
                spaceAfter=2
            )
            meta_box_style = ParagraphStyle(
                'MetaBoxStyle',
                parent=styles['Normal'],
                fontName=main_font,
                fontSize=7.5,
                leading=9.5,
                textColor=TEXT_MUTED,
                alignment=1
            )

            # Table Typography Styles
            header_cell_style = ParagraphStyle(
                'HeaderCellStyle',
                parent=styles['Normal'],
                fontName=bold_font,
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=0
            )
            header_center_style = ParagraphStyle(
                'HeaderCenterStyle',
                parent=header_cell_style,
                alignment=1
            )
            header_right_style = ParagraphStyle(
                'HeaderRightStyle',
                parent=header_cell_style,
                alignment=2
            )

            cell_style = ParagraphStyle(
                'BodyCellStyle',
                parent=styles['Normal'],
                fontName=main_font,
                fontSize=7.5,
                leading=9.5,
                textColor=TEXT_DARK
            )
            cell_center = ParagraphStyle(
                'BodyCellCenter',
                parent=cell_style,
                alignment=1
            )
            cell_right = ParagraphStyle(
                'BodyCellRight',
                parent=cell_style,
                alignment=2
            )

            meta_summary_text = f"<b>Generated:</b> {gen_timestamp} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Filters:</b> {active_filter_str} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Total Records:</b> {records.count()}"

            # Top Centered Official Municipal Logo
            logo_path = os.path.join(settings.BASE_DIR, 'assets', 'carigara_logo.png')
            if os.path.exists(logo_path):
                logo_img = Image(logo_path, width=40, height=40)
                logo_img.hAlign = 'CENTER'
                story.append(logo_img)
                story.append(Spacer(1, 2))

            story.append(Paragraph("REPUBLIC OF THE PHILIPPINES &bull; PROVINCE OF LEYTE", sub_header_style))
            story.append(Paragraph("MUNICIPALITY OF CARIGARA &bull; OFFICE OF THE MUNICIPAL ENGINEER", office_title_style))
            story.append(Paragraph("ENGINEERING RECORDS SUMMARY REPORT", report_title_style))
            story.append(Paragraph(meta_summary_text, meta_box_style))
            story.append(Spacer(1, 6))

            # Column Widths (Total: 720pt across landscape letter with 36pt margins)
            col_widths = [35, 135, 80, 75, 30, 55, 85, 85, 80, 45]
            table_data = [[
                Paragraph("ID", header_center_style),
                Paragraph("Record Title", header_cell_style),
                Paragraph("Type", header_cell_style),
                Paragraph("Barangay", header_cell_style),
                Paragraph("Year", header_center_style),
                Paragraph("Status", header_center_style),
                Paragraph("Applicant", header_cell_style),
                Paragraph("Contractor", header_cell_style),
                Paragraph("Cost / Budget (₱)", header_right_style),
                Paragraph("Uploads", header_center_style)
            ]]

            violation_rows_info = {} # row_idx -> bg_color
            total_val = 0
            for row_idx, r in enumerate(records, 1):
                is_violation = bool(r.is_illegal_construction)
                violation_status = r.illegal_compliance_status or 'unresolved'

                if is_violation:
                    if violation_status == 'unresolved':
                        status_html = '<font color="#B91C1C"><b>Unresolved</b></font>'
                        violation_rows_info[row_idx] = colors.HexColor('#FFF1F2')
                    elif violation_status == 'pending_permit':
                        status_html = '<font color="#B45309"><b>Permit Filed</b></font>'
                        violation_rows_info[row_idx] = colors.HexColor('#FFFBEB')
                    elif violation_status == 'resolved':
                        status_html = '<font color="#15803D"><b>Regularized</b></font>'
                        violation_rows_info[row_idx] = colors.HexColor('#F0FDF4')
                    else:
                        status_html = '<font color="#B91C1C"><b>Violation</b></font>'
                        violation_rows_info[row_idx] = colors.HexColor('#FFF1F2')
                else:
                    status_label = dict(EngineeringRecord.STATUS_CHOICES).get(r.status, r.status)
                    status_html = status_label
                
                # Resolve Record Title cleanly
                if r.record_type == 'Permit':
                    permit_num = (r.permit_detail.permit_number.strip() if hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.permit_number else '').strip()
                    if permit_num:
                        ref_no = permit_num
                    elif r.title and r.title.strip() and r.title.strip() != '—' and not r.is_illegal_construction and r.title.strip().lower() != 'permit':
                        ref_no = r.title.strip()
                    elif r.is_illegal_construction:
                        ref_no = f"Violation #{r.record_id}"
                    else:
                        ref_no = f"Permit #{r.record_id}"
                else:
                    ref_no = r.title.strip() if r.title and r.title.strip() and r.title.strip() != '—' else f"Project #{r.record_id}"

                # Resolve Specific Type
                if r.record_type == 'Permit':
                    if is_violation:
                        if violation_status == 'resolved':
                            specific_type = '<font color="#15803D"><b>Regularized Building</b></font>'
                        elif violation_status == 'pending_permit':
                            specific_type = '<font color="#B45309"><b>Violation (Permit Filed)</b></font>'
                        else:
                            specific_type = '<font color="#B91C1C"><b>Violation Report</b></font>'
                    elif hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.permit_type:
                        specific_type = r.specific_type_label
                    else:
                        specific_type = "Building Permit"
                else:
                    if hasattr(r, 'project_detail') and r.project_detail and r.project_detail.project_type:
                        specific_type = r.specific_type_label
                    else:
                        specific_type = f"{r.project_scope} Project" if r.project_scope else "Project"

                # Resolve Applicant and Contractor separately
                applicant_val = "—"
                contractor_val = "—"
                if r.record_type == 'Permit':
                    app_name = (r.permit_detail.applicant_name.strip() if hasattr(r, 'permit_detail') and r.permit_detail and r.permit_detail.applicant_name else '').strip()
                    if app_name and app_name.lower() not in ['n/a', 'none', 'if applicable', '', '—'] and not app_name.startswith('[') and 'unpermitted' not in app_name.lower() and 'violation' not in app_name.lower():
                        applicant_val = app_name
                else:
                    c_name = (r.project_detail.contractor.strip() if hasattr(r, 'project_detail') and r.project_detail and r.project_detail.contractor else '').strip()
                    if c_name and c_name.lower() not in ['n/a', 'none', 'if applicable', '', '—'] and not c_name.startswith('[') and 'unpermitted' not in c_name.lower() and 'violation' not in c_name.lower():
                        contractor_val = c_name

                # Resolve Cost / Budget
                cost = 0
                if r.record_type == 'Project' and hasattr(r, 'project_detail') and r.project_detail and r.project_detail.project_cost:
                    cost = r.project_detail.project_cost
                    total_val += cost

                # Resolve Upload Completion Status
                c_stats = r.completion_stats
                if c_stats['total'] > 0:
                    if c_stats['is_complete']:
                        doc_para = Paragraph(f'<font color="#15803D"><b>{c_stats["fulfilled"]}/{c_stats["total"]}</b></font>', cell_center)
                    elif c_stats['fulfilled'] > 0:
                        doc_para = Paragraph(f'<font color="#B45309">{c_stats["fulfilled"]}/{c_stats["total"]}</font>', cell_center)
                    else:
                        doc_para = Paragraph(f'<font color="#B91C1C">0/{c_stats["total"]}</font>', cell_center)
                else:
                    doc_para = Paragraph(f'<font color="#64748B">{r.documents.count()} files</font>' if is_violation else '<font color="#94A3B8">—</font>', cell_center)

                barangay_name = r.barangay.barangay_name if r.barangay else "—"
                year_val = str(r.year) if r.year else "—"

                table_data.append([
                    Paragraph(str(r.record_id), cell_center),
                    Paragraph(ref_no, cell_style),
                    Paragraph(specific_type, cell_style),
                    Paragraph(barangay_name, cell_style),
                    Paragraph(year_val, cell_center),
                    Paragraph(status_html, cell_center),
                    Paragraph(applicant_val if applicant_val != '—' else '<font color="#94A3B8">—</font>', cell_style),
                    Paragraph(contractor_val if contractor_val != '—' else '<font color="#94A3B8">—</font>', cell_style),
                    Paragraph(f"₱ {cost:,.2f}" if cost > 0 else '<font color="#94A3B8">—</font>', cell_right),
                    doc_para
                ])

            # Total summary row
            total_label_style = ParagraphStyle('TotalLabel', parent=cell_style, fontName=bold_font, fontSize=8, textColor=NAVY)
            total_right_style = ParagraphStyle('TotalRight', parent=cell_right, fontName=bold_font, fontSize=8, textColor=NAVY)
            
            table_data.append([
                Paragraph("<b>TOTAL</b>", ParagraphStyle('TotCenter', parent=cell_center, fontName=bold_font, fontSize=8, textColor=NAVY)),
                Paragraph(f"<b>{records.count()} Record(s)</b>", total_label_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph("<b>Total Budget:</b>", total_right_style),
                Paragraph(f"<b>₱ {total_val:,.2f}</b>", total_right_style),
                Paragraph("", cell_style)
            ])

            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Construct styling with alternating row backgrounds
            t_style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), NAVY),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 4),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#E2E8F0')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#EEF2F6')),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#94A3B8')),
                ('LINEBELOW', (0, -1), (-1, -1), 1.5, NAVY),
                ('TOPPADDING', (0, -1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 5),
            ]

            for row_i in range(1, len(table_data) - 1):
                if row_i in violation_rows_info:
                    bg = violation_rows_info[row_i]
                else:
                    bg = colors.HexColor('#F8FAFC') if row_i % 2 == 0 else colors.HexColor('#FFFFFF')
                
                t_style_cmds.append(('BACKGROUND', (0, row_i), (-1, row_i), bg))
                t_style_cmds.append(('TOPPADDING', (0, row_i), (-1, row_i), 3))
                t_style_cmds.append(('BOTTOMPADDING', (0, row_i), (-1, row_i), 3))

            t.setStyle(TableStyle(t_style_cmds))
            story.append(t)

            # Official Sign-off block
            sign_style_left = ParagraphStyle('SignLeft', parent=styles['Normal'], fontName=main_font, fontSize=8, leading=12, textColor=TEXT_DARK)
            sign_style_right = ParagraphStyle('SignRight', parent=styles['Normal'], fontName=main_font, fontSize=8, leading=12, textColor=TEXT_DARK, alignment=2)
            
            signatory_data = [
                [
                    Paragraph(f"<b>Prepared &amp; Exported by:</b><br/><br/><br/><u><b>{request.user.full_name or request.user.username}</b></u><br/>{request.user.get_role_display()}", sign_style_left),
                    Paragraph("<b>Certified Correct:</b><br/><br/><br/><u><b>MUNICIPAL ENGINEER</b></u><br/>Municipal Engineering Office — Carigara, Leyte", sign_style_right)
                ]
            ]
            sign_table = Table(signatory_data, colWidths=[360, 360])
            sign_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 16),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))

            story.append(KeepTogether([
                Spacer(1, 14),
                sign_table
            ]))

            doc.build(story, canvasmaker=NumberedCanvas)
            pdf_data = buffer.getvalue()
            buffer.close()

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=eTala_Engineering_Records_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf'
            response.write(pdf_data)
            return response

    total_count = records.count()
    total_active = records.exclude(status='archived').count()
    total_archived = records.filter(status='archived').count()

    # Category breakdown (sums exactly to total_count since all records are either Permit or Project)
    by_category = [
        {
            'category_name': 'Permit Records',
            'count': records.filter(record_type='Permit').count()
        },
        {
            'category_name': 'Municipal Projects',
            'count': records.filter(record_type='Project', project_scope='Municipal').count()
        },
        {
            'category_name': 'Barangay Projects',
            'count': records.filter(record_type='Project', project_scope='Barangay').count()
        }
    ]

    # Group by Barangay
    by_barangay = list(records.values('barangay__barangay_name').annotate(count=Count('record_id')).order_by('-count'))

    # Group by Year
    by_year = list(records.values('year').annotate(count=Count('record_id')).order_by('-year'))

    # Growth data (last 6 months) respecting filters
    import datetime
    growth_data = []
    today = timezone.now()
    
    # We apply category, barangay, and year filters to growth history
    growth_records = EngineeringRecord.objects.all()
    if selected_record_type:
        growth_records = growth_records.filter(record_type=selected_record_type)
    if selected_barangay:
        growth_records = growth_records.filter(barangay_id=selected_barangay)
    if selected_year:
        growth_records = growth_records.filter(year=selected_year)

    for i in range(5, -1, -1):
        year_val = today.year
        month_val = today.month - i
        if month_val <= 0:
            month_val += 12
            year_val -= 1
        first_day_of_next_month = (datetime.datetime(year_val, month_val, 1) + datetime.timedelta(days=32)).replace(day=1)
        first_day_of_next_month = timezone.make_aware(first_day_of_next_month)
        cumulative_count = growth_records.filter(created_at__lt=first_day_of_next_month).count()
        month_name = datetime.date(year_val, month_val, 1).strftime('%b %Y')
        growth_data.append({'month': month_name, 'count': cumulative_count})

    # Prepare readable filter names for UI display
    active_filters = []
    if selected_record_type:
        active_filters.append(f"Category: {selected_record_type}s")
    if selected_barangay:
        barangay_obj = Barangay.objects.filter(barangay_id=selected_barangay).first()
        if barangay_obj:
            active_filters.append(f"Barangay: {barangay_obj.barangay_name}")
    if selected_year:
        active_filters.append(f"Year: {selected_year}")
    if selected_status:
        status_name = dict(EngineeringRecord.STATUS_CHOICES).get(selected_status, selected_status)
        active_filters.append(f"Status: {status_name}")

    # ── PDF GUIDE COMPLIANT SUMMARY METRICS ──
    today_date = timezone.now().date()

    # 1. Project Summary Metrics
    projects_qs = records.filter(record_type='Project')
    total_projects = projects_qs.count()
    municipal_projects_count = projects_qs.filter(project_scope='Municipal').count()
    barangay_projects_count = projects_qs.filter(project_scope='Barangay').count()
    
    # 2. Permit Status & Expiration Metrics
    permits_qs = records.filter(record_type='Permit')
    total_permits = permits_qs.count()
    
    building_permits_count = permits_qs.filter(permit_detail__permit_type__iexact='Building').count()
    occupancy_permits_count = permits_qs.filter(permit_detail__permit_type__iexact='Occupancy').count()
    fencing_permits_count = permits_qs.filter(permit_detail__permit_type__iexact='Fencing').count()
    electrical_permits_count = permits_qs.filter(permit_detail__permit_type__iexact='Electrical').count()

    expiring_permits_qs = permits_qs.select_related('permit_detail', 'barangay').prefetch_related('documents')
    
    expiring_soon_list = []
    expired_count = 0
    expiring_soon_count = 0
    valid_permits_count = 0

    for p in expiring_permits_qs:
        permit_det = getattr(p, 'permit_detail', None)
        exp_date = None
        # Use prefetched documents to avoid executing a separate DB query for every single permit
        docs = [d for d in p.documents.all() if d.expiry_date is not None]
        if docs:
            docs.sort(key=lambda d: d.expiry_date)
            exp_date = docs[0].expiry_date
        elif permit_det and permit_det.date_issued:
            import datetime
            exp_date = permit_det.date_issued + datetime.timedelta(days=365)

        if exp_date:
            days_left = (exp_date - today_date).days
            permit_num = permit_det.permit_number if (permit_det and permit_det.permit_number) else f"BP-{p.year or 2026}-{p.record_id:03d}"
            applicant = permit_det.applicant_name if (permit_det and permit_det.applicant_name) else "N/A"
            if days_left < 0:
                expired_count += 1
                if len(expiring_soon_list) < 10:
                    expiring_soon_list.append({
                        'record_id': p.record_id,
                        'permit_number': permit_num,
                        'applicant_name': applicant,
                        'barangay_name': p.barangay.barangay_name if p.barangay else "Unassigned",
                        'expiry_date': exp_date,
                        'days_left': abs(days_left),
                        'is_expired': True
                    })
            elif days_left <= 30:
                expiring_soon_count += 1
                if len(expiring_soon_list) < 10:
                    expiring_soon_list.append({
                        'record_id': p.record_id,
                        'permit_number': permit_num,
                        'applicant_name': applicant,
                        'barangay_name': p.barangay.barangay_name if p.barangay else "Unassigned",
                        'expiry_date': exp_date,
                        'days_left': days_left,
                        'is_expired': False
                    })
            else:
                valid_permits_count += 1
        else:
            valid_permits_count += 1

    # If all permits have no expiry date, set default valid permits count
    if total_permits > 0 and (expired_count + expiring_soon_count + valid_permits_count) == 0:
        valid_permits_count = total_permits

    # 3. Illegal Construction Metrics
    illegal_cases_qs = records.filter(is_illegal_construction=True)
    total_illegal_cases = illegal_cases_qs.count()
    active_illegal_cases = illegal_cases_qs.exclude(illegal_compliance_status='resolved').count()
    resolved_illegal_cases = illegal_cases_qs.filter(illegal_compliance_status='resolved').count()
    illegal_cases_list = illegal_cases_qs.select_related('barangay')[:6]

    # 4. Document Completion Metrics
    completed_records_count = 0
    for rec in records:
        if rec.completion_stats.get('is_complete', False):
            completed_records_count += 1
    completion_rate_pct = round((completed_records_count / total_count * 100)) if total_count > 0 else 100

    barangays = Barangay.objects.all()

    context = {
        'total_count': total_count,
        'total_active': total_active,
        'total_archived': total_archived,
        'total_projects': total_projects,
        'municipal_projects_count': municipal_projects_count,
        'barangay_projects_count': barangay_projects_count,
        'total_permits': total_permits,
        'building_permits_count': building_permits_count,
        'occupancy_permits_count': occupancy_permits_count,
        'fencing_permits_count': fencing_permits_count,
        'electrical_permits_count': electrical_permits_count,
        'valid_permits_count': valid_permits_count,
        'expiring_soon_count': expiring_soon_count,
        'expired_count': expired_count,
        'expiring_soon_list': expiring_soon_list,
        'total_illegal_cases': total_illegal_cases,
        'active_illegal_cases': active_illegal_cases,
        'resolved_illegal_cases': resolved_illegal_cases,
        'illegal_cases_list': illegal_cases_list,
        'completed_records_count': completed_records_count,
        'completion_rate_pct': completion_rate_pct,
        'by_category': by_category,
        'by_barangay': by_barangay,
        'by_year': by_year,
        'growth_data': growth_data,
        'barangays': barangays,
        'selected_record_type': selected_record_type,
        'selected_barangay': selected_barangay,
        'selected_year': selected_year,
        'selected_status': selected_status,
        'status_choices': EngineeringRecord.STATUS_CHOICES,
        'year_choices': get_year_choices(),
        'active_filters': active_filters,
        'active_tab': 'reports',
    }
    return render(request, 'permits/reports.html', context)



# ─── ACTIVITY LOGS ──────────────────────────────────────────────────────────

@login_required
def activity_logs_view(request):
    if request.user.role not in ['admin', 'staff', 'engineer']:
        raise PermissionDenied("You do not have permission to view activity logs.")

    if request.method == 'POST':
        if request.user.role != 'admin':
            return HttpResponseForbidden("Unauthorized action.")
        action = request.POST.get('action')
        if action == 'block_ip':
            ip = request.POST.get('ip_address')
            if ip:
                BlockedIP.objects.get_or_create(ip_address=ip, blocked_by=request.user)
                log_audit(request.user, f"Blocked IP address: {ip}", request=request)
                messages.success(request, f"Successfully blocked IP address: {ip}")
            return redirect('activity_logs')
        elif action == 'unblock_ip':
            ip = request.POST.get('ip_address')
            if ip:
                BlockedIP.objects.filter(ip_address=ip).delete()
                log_audit(request.user, f"Unblocked IP address: {ip}", request=request)
                messages.success(request, f"Successfully unblocked IP address: {ip}")
            return redirect('activity_logs')
        elif action == 'block_email':
            email = request.POST.get('email', '').strip()
            ip = request.POST.get('ip_address', '').strip()
            if email:
                user_obj = CustomUser.objects.filter(email__iexact=email).first()
                if user_obj:
                    user_obj.is_active = False
                    user_obj.save()
                if ip:
                    BlockedIP.objects.get_or_create(ip_address=ip, blocked_by=request.user)
                log_audit(request.user, f"Blocked login for email: {email}", request=request)
                messages.success(request, f"Successfully blocked email access for: {email}")
            return redirect('activity_logs')
        elif action == 'unblock_email':
            email = request.POST.get('email', '').strip()
            ip = request.POST.get('ip_address', '').strip()
            if email:
                user_obj = CustomUser.objects.filter(email__iexact=email).first()
                if user_obj:
                    user_obj.is_active = True
                    user_obj.save()
                if ip:
                    BlockedIP.objects.filter(ip_address=ip).delete()
                log_audit(request.user, f"Unblocked login for email: {email}", request=request)
                messages.success(request, f"Successfully restored email access for: {email}")
            return redirect('activity_logs')

    # 1. Audit Logs (System Activity Log)
    audit_logs = AuditLog.objects.select_related('user').order_by('-performed_at')
    if request.user.role != 'admin':
        audit_logs = audit_logs.filter(user=request.user)

    query = request.GET.get('q', '').strip()
    if query:
        audit_logs = audit_logs.filter(
            Q(action__icontains=query) | Q(user__username__icontains=query) | Q(user__full_name__icontains=query) | Q(user__email__icontains=query)
        )

    # Date Range Filter
    date_filter = request.GET.get('date_range', 'all').strip()
    now = timezone.now()
    if date_filter == 'today':
        audit_logs = audit_logs.filter(performed_at__date=now.date())
    elif date_filter == '7days':
        audit_logs = audit_logs.filter(performed_at__gte=now - timedelta(days=7))
    elif date_filter == '30days':
        audit_logs = audit_logs.filter(performed_at__gte=now - timedelta(days=30))

    # Action Type Filter
    action_type = request.GET.get('action_type', 'all').strip()
    if action_type == 'create':
        audit_logs = audit_logs.filter(Q(action__icontains='created') | Q(action__icontains='added'))
    elif action_type == 'update':
        audit_logs = audit_logs.filter(Q(action__icontains='updated') | Q(action__icontains='modified'))
    elif action_type == 'upload':
        audit_logs = audit_logs.filter(action__icontains='uploaded')
    elif action_type == 'delete':
        audit_logs = audit_logs.filter(Q(action__icontains='deleted') | Q(action__icontains='removed'))

    per_page = get_per_page(request, 15)
    audit_paginator = Paginator(audit_logs, per_page)
    log_page_obj = audit_paginator.get_page(request.GET.get('log_page'))

    # 2. Login History Attempts
    login_page_obj = None
    status_filter = 'all'
    if request.user.role == 'admin':
        login_attempts = LoginAttempt.objects.all().order_by('-timestamp')
        if query:
            login_attempts = login_attempts.filter(
                Q(email_attempted__icontains=query) | Q(ip_address__icontains=query)
            )

        if date_filter == 'today':
            login_attempts = login_attempts.filter(timestamp__date=now.date())
        elif date_filter == '7days':
            login_attempts = login_attempts.filter(timestamp__gte=now - timedelta(days=7))
        elif date_filter == '30days':
            login_attempts = login_attempts.filter(timestamp__gte=now - timedelta(days=30))

        status_filter = request.GET.get('status', 'all').strip()
        if status_filter == 'success':
            login_attempts = login_attempts.filter(success=True)
        elif status_filter == 'failed':
            login_attempts = login_attempts.filter(success=False)

        login_paginator = Paginator(login_attempts, per_page)
        login_page_obj = login_paginator.get_page(request.GET.get('login_page'))

    # Fetch currently blocked IP addresses
    blocked_ips = []
    if request.user.role == 'admin':
        blocked_ips = list(BlockedIP.objects.values_list('ip_address', flat=True))

    context = {
        'per_page': per_page,
        'log_page_obj': log_page_obj,
        'login_page_obj': login_page_obj,
        'query': query,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'action_type': action_type,
        'blocked_ips': blocked_ips,
        'active_tab': 'activity_logs',
    }
    return render(request, 'permits/activity_logs.html', context)


class Echo:
    def write(self, value):
        return value

@login_required
def export_activity_logs_view(request):
    if request.user.role not in ['admin', 'staff', 'engineer']:
        raise PermissionDenied("You do not have permission to export activity logs.")
        
    tab = request.GET.get('tab', 'audit').strip()
    query = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date_range', 'all').strip()
    action_type = request.GET.get('action_type', 'all').strip()
    export_format = request.GET.get('format', 'pdf').strip().lower()

    if export_format == 'csv':
        filename, row_gen = build_activity_logs_csv_rows(tab, query, date_filter, action_type, request.user)
        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)
        response = StreamingHttpResponse(
            (writer.writerow(row) for row in row_gen()),
            content_type="text/csv"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        log_audit(request.user, f"Exported {tab.capitalize()} Activity Logs to CSV", request=request)
        return response

    # ── DEFAULT: Direct PDF Export via ReportLab ──
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    th_style = ParagraphStyle(
        'THStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    td_style = ParagraphStyle(
        'TDStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#1e293b')
    )
    td_badge = ParagraphStyle(
        'TDBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#1e40af')
    )

    elements = []

    # Header section with Logo
    logo_path = os.path.join(settings.BASE_DIR, 'assets', 'carigara_logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=42, height=42)
        header_text = [
            Paragraph("REPUBLIC OF THE PHILIPPINES &bull; PROVINCE OF LEYTE", subtitle_style),
            Paragraph("MUNICIPALITY OF CARIGARA &bull; MUNICIPAL ENGINEERING OFFICE", subtitle_style),
            Spacer(1, 2),
            Paragraph("OFFICIAL SECURITY AUDIT &amp; ACTIVITY TRAIL REPORT", title_style)
        ]
        header_table = Table([[img, header_text]], colWidths=[55, 665])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ]))
        elements.append(header_table)
    else:
        elements.append(Paragraph("MUNICIPALITY OF CARIGARA &bull; MUNICIPAL ENGINEERING OFFICE", subtitle_style))
        elements.append(Paragraph("OFFICIAL SECURITY AUDIT &amp; ACTIVITY TRAIL REPORT", title_style))

    elements.append(Spacer(1, 10))

    # Meta banner
    now_pst = timezone.now()
    tab_title = "Authentication & Login History" if (tab == 'login' and request.user.role == 'admin') else "System Activity & Record Audit Trail"
    meta_p = Paragraph(
        f"<b>Log Scope:</b> {tab_title} &nbsp;|&nbsp; <b>Generated By:</b> {request.user.full_name or request.user.username} ({request.user.get_role_display()}) &nbsp;|&nbsp; <b>Generated At:</b> {now_pst.strftime('%B %d, %Y %I:%M %p')} PST",
        meta_style
    )
    meta_box = Table([[meta_p]], colWidths=[720])
    meta_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_box)
    elements.append(Spacer(1, 10))

    # Query Data
    if tab == 'login' and request.user.role == 'admin':
        qs = LoginAttempt.objects.all().order_by('-timestamp')
        if date_filter == 'today':
            qs = qs.filter(timestamp__date=now_pst.date())
        elif date_filter == '7days':
            qs = qs.filter(timestamp__gte=now_pst - timedelta(days=7))
        elif date_filter == '30days':
            qs = qs.filter(timestamp__gte=now_pst - timedelta(days=30))
        if action_type == 'success':
            qs = qs.filter(success=True)
        elif action_type == 'failed':
            qs = qs.filter(success=False)
        if query:
            qs = qs.filter(Q(email_attempted__icontains=query) | Q(ip_address__icontains=query))

        table_data = [[
            Paragraph("#", th_style),
            Paragraph("TIMESTAMP (PST)", th_style),
            Paragraph("EMAIL ATTEMPTED", th_style),
            Paragraph("LOGIN STATUS", th_style),
            Paragraph("IP ADDRESS", th_style)
        ]]
        for idx, item in enumerate(qs[:1000], start=1):
            status_text = "SUCCESSFUL" if item.success else "FAILED"
            status_color = "#16a34a" if item.success else "#dc2626"
            status_p = Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", td_style)
            table_data.append([
                Paragraph(str(idx), td_style),
                Paragraph(item.timestamp.strftime("%Y-%m-%d %H:%M:%S"), td_style),
                Paragraph(item.email_attempted or "Unknown", td_style),
                status_p,
                Paragraph(item.ip_address or "N/A", td_style)
            ])
        col_widths = [35, 130, 240, 135, 180]
    else:
        qs = AuditLog.objects.all().select_related('user').order_by('-performed_at')
        if request.user.role != 'admin':
            qs = qs.filter(user=request.user)
        if date_filter == 'today':
            qs = qs.filter(performed_at__date=now_pst.date())
        elif date_filter == '7days':
            qs = qs.filter(performed_at__gte=now_pst - timedelta(days=7))
        elif date_filter == '30days':
            qs = qs.filter(performed_at__gte=now_pst - timedelta(days=30))
        if action_type and action_type != 'all':
            qs = qs.filter(action__icontains=action_type)
        if query:
            qs = qs.filter(Q(action__icontains=query) | Q(user__username__icontains=query) | Q(user__full_name__icontains=query))

        table_data = [[
            Paragraph("#", th_style),
            Paragraph("DATE &amp; TIME", th_style),
            Paragraph("OPERATOR / STAFF", th_style),
            Paragraph("OFFICIAL ROLE", th_style),
            Paragraph("ACTION EXECUTED", th_style),
            Paragraph("IP ADDRESS", th_style)
        ]]
        for idx, item in enumerate(qs[:1000], start=1):
            if item.user:
                user_str = item.user.full_name or item.user.username
                role_str = item.user.get_role_display()
            else:
                user_str = "System"
                role_str = "System"
            table_data.append([
                Paragraph(str(idx), td_style),
                Paragraph(item.performed_at.strftime("%Y-%m-%d %H:%M:%S"), td_style),
                Paragraph(user_str, td_badge),
                Paragraph(role_str, td_style),
                Paragraph(item.action, td_style),
                Paragraph(item.ip_address or "N/A", td_style)
            ])
        col_widths = [30, 115, 140, 105, 230, 100]

    log_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    log_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(log_table)

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_footer(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_footer(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor('#64748b'))
            self.drawString(36, 20, "CONFIDENTIAL & OFFICIAL RECORD \u2022 eTala Municipal Engineering Office")
            self.drawRightString(792 - 36, 20, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

    doc.build(elements, canvasmaker=NumberedCanvas)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"eTala_Activity_Logs_{tab}_{now_pst.strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    log_audit(request.user, f"Exported {tab.capitalize()} Activity Logs to PDF", request=request)
    return response


@login_required
def serve_user_avatar_view(request, user_id):
    """Securely streams a user's profile avatar picture with browser caching from Supabase storage."""
    target_user = get_object_or_404(CustomUser, pk=user_id)
    if not target_user.profile_picture:
        raise Http404("User has no profile picture.")

    try:
        if not target_user.profile_picture.storage.exists(target_user.profile_picture.name):
            # Auto-heal orphaned DB pointer to prevent 404 console spam
            target_user.profile_picture = None
            target_user.save(update_fields=['profile_picture'])
            raise Http404("Avatar file not found in cloud storage.")
        file_obj = target_user.profile_picture.open('rb')
        filename = os.path.basename(target_user.profile_picture.name)
        content_type, _ = mimetypes.guess_type(filename)
        response = FileResponse(file_obj, content_type=content_type or 'image/jpeg')
        response['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception as e:
        if not isinstance(e, Http404):
            logger.warning(f"Error serving profile picture for user {user_id}: {e}")
        raise Http404("Avatar file unavailable.")


# ─── PROFILE ─────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'upload_photo':
            if 'profile_picture' in request.FILES:
                try:
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()
                    log_audit(user, "Updated profile picture", request=request)
                    messages.success(request, "Profile picture updated successfully.")
                except Exception as e:
                    logger.error(f"Error uploading profile picture: {str(e)}")
                    messages.error(request, "Upload failed or timed out due to network connection. Please check your internet and try again.")
            else:
                messages.error(request, "No image file provided.")
            return redirect('profile')

        elif action == 'remove_photo':
            if user.profile_picture:
                try:
                    user.profile_picture.delete(save=False)
                    user.profile_picture = None
                    user.save()
                    log_audit(user, "Removed profile picture", request=request)
                    messages.success(request, "Profile picture removed.")
                except Exception as e:
                    logger.error(f"Error deleting profile picture: {str(e)}")
                    messages.error(request, "Failed to remove photo due to network connection. Please try again.")
            return redirect('profile')

        elif action == 'update_profile':
            full_name = sanitize_input(request.POST.get('full_name', '')).strip()
            email = sanitize_input(request.POST.get('email', '')).lower()

            if not full_name or not email:
                messages.error(request, "Full Name and Email are required.")
                return redirect('profile')

            if CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, "Email already in use.")
                return redirect('profile')

            user.full_name = full_name
            user.email = email
            user.save()
            log_audit(user, "Updated profile details", request=request)
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')

        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_new_password = request.POST.get('confirm_new_password', '')

            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect('profile')

            if new_password != confirm_new_password:
                messages.error(request, "New passwords do not match.")
                return redirect('profile')

            ok, err_msg = validate_password_strength(new_password)
            if not ok:
                messages.error(request, err_msg)
                return redirect('profile')

            matched_history = False
            histories = PasswordHistory.objects.filter(user=user).order_by('-created_at')[:3]
            for h in histories:
                if check_password(new_password, h.password_hash):
                    matched_history = True
                    break

            if check_password(new_password, user.password):
                matched_history = True

            if matched_history:
                messages.error(request, "Cannot reuse the last 3 passwords.")
                return redirect('profile')

            PasswordHistory.objects.create(user=user, password_hash=user.password)

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)

            all_histories = PasswordHistory.objects.filter(user=user).order_by('-created_at')
            if all_histories.count() > 3:
                for h in all_histories[3:]:
                    h.delete()

            log_audit(user, "Changed password", request=request)
            messages.success(request, "Password changed successfully.")
            return redirect('profile')

    user_logs = AuditLog.objects.filter(user=user).order_by('-performed_at')[:10]

    context = {
        'user_logs': user_logs,
        'active_tab': 'profile',
    }
    return render(request, 'permits/profile.html', context)


# ─── ADMIN SETTINGS ──────────────────────────────────────────────────────────

import os


@login_required
def settings_view(request):
    if request.user.role != 'admin':
        raise PermissionDenied("You do not have permission to view Settings.")

    templates = RequirementTemplate.objects.all().prefetch_related('items')
    barangays = Barangay.objects.all()
    office_settings = get_office_settings()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_expiry_alerts':
            success, msg = send_document_expiry_alerts()
            log_audit(request.user, f"Triggered Document Expiry Email Alerts: {msg}", request=request)
            if success:
                messages.success(request, f"Email notification summary sent successfully: {msg}")
            else:
                messages.warning(request, msg)
            return redirect(f"{reverse('settings')}?tab=maintenance")

        if action == 'clear_failed_logins':

            count = LoginAttempt.objects.filter(success=False).delete()[0]
            log_audit(request.user, f"Cleared {count} failed login attempt logs", request=request)
            messages.success(request, f"Successfully cleared {count} failed login attempt logs.")
            return redirect(f"{reverse('settings')}?tab=logs")

        if action == 'update_office_info':
            office_name = sanitize_input(request.POST.get('office_name', '')).strip()
            municipality = sanitize_input(request.POST.get('municipality', '')).strip()
            province = sanitize_input(request.POST.get('province', '')).strip()
            save_office_settings(office_name, municipality, province)
            log_audit(request.user, f"Updated office settings: {office_name}, {municipality}", request=request)
            messages.success(request, "Office configuration settings updated successfully.")
            return redirect('settings')

        elif action == 'create_template':
            record_type = sanitize_input(request.POST.get('record_type', '')).strip()
            subtype = sanitize_input(request.POST.get('subtype', '')).strip()
            scope = sanitize_input(request.POST.get('scope', '')).strip()
            
            exists = RequirementTemplate.objects.filter(record_type=record_type, subtype=subtype, scope=scope).exists()
            if exists:
                messages.error(request, f"A template for {record_type} — {subtype} ({scope or 'N/A'}) already exists.")
            else:
                tmpl = RequirementTemplate.objects.create(record_type=record_type, subtype=subtype, scope=scope)
                log_audit(request.user, f"Created checklist template: {tmpl}", request=request)
                messages.success(request, f"Successfully created checklist template: {tmpl}")
            return redirect(f"{reverse('settings')}?tab=templates")
            
        elif action == 'edit_template':
            template_id = request.POST.get('template_id')
            tmpl = get_object_or_404(RequirementTemplate, pk=template_id)
            tmpl.subtype = sanitize_input(request.POST.get('subtype', '')).strip()
            tmpl.scope = sanitize_input(request.POST.get('scope', '')).strip()
            tmpl.is_active = request.POST.get('is_active') == 'true'
            tmpl.save()
            log_audit(request.user, f"Updated checklist template details: {tmpl}", request=request)
            messages.success(request, "Checklist template details updated successfully.")
            return redirect(f"{reverse('settings')}?tab=templates&template_id={tmpl.template_id}")

        elif action == 'add_requirement_item':
            template_id = request.POST.get('template_id')
            tmpl = get_object_or_404(RequirementTemplate, pk=template_id)
            name = sanitize_input(request.POST.get('name', '')).strip()
            description = sanitize_input(request.POST.get('description', '')).strip()
            is_required = request.POST.get('is_required') == 'true'
            is_group = request.POST.get('is_group') == 'true'
            parent_id = request.POST.get('parent_id') or None
            
            parent_obj = None
            if parent_id:
                parent_obj = get_object_or_404(RequirementItem, pk=parent_id, template=tmpl)
                parent_obj.is_group = True
                parent_obj.save()
                is_group = False  # Children cannot be groups themselves in 2-level hierarchy

            max_order = tmpl.items.filter(parent=parent_obj).count() + 1

            item = RequirementItem.objects.create(
                template=tmpl,
                parent=parent_obj,
                is_group=is_group,
                name=name,
                description=description,
                is_required=is_required,
                order=max_order
            )
            item_type_label = "document group" if is_group else ("sub-requirement" if parent_obj else "requirement")
            log_audit(request.user, f"Added {item_type_label} '{name}' to template '{tmpl}'", request=request)
            messages.success(request, f"Added {item_type_label} '{name}' successfully.")
            return redirect(f"{reverse('settings')}?tab=templates&template_id={tmpl.template_id}")

        elif action == 'edit_requirement_item':
            item_id = request.POST.get('item_id')
            template_id = request.POST.get('template_id')
            item = get_object_or_404(RequirementItem, pk=item_id)
            old_name = item.name
            item.name = sanitize_input(request.POST.get('name', '')).strip()
            item.description = sanitize_input(request.POST.get('description', '')).strip()
            item.is_required = request.POST.get('is_required') == 'true'
            if 'is_group' in request.POST:
                item.is_group = request.POST.get('is_group') == 'true'
            
            if 'parent_id' in request.POST:
                parent_id = request.POST.get('parent_id') or None
                if parent_id and parent_id != str(item.item_id):
                    parent_obj = get_object_or_404(RequirementItem, pk=parent_id, template=item.template)
                    parent_obj.is_group = True
                    parent_obj.save()
                    item.parent = parent_obj
                    item.is_group = False
                elif not parent_id:
                    item.parent = None
                    
            item.save()
            log_audit(request.user, f"Updated requirement '{old_name}' to '{item.name}'", request=request)
            messages.success(request, f"Requirement '{item.name}' updated successfully.")
            return redirect(f"{reverse('settings')}?tab=templates&template_id={template_id}")

        elif action == 'delete_requirement_item':
            item_id = request.POST.get('item_id')
            template_id = request.POST.get('template_id')
            item = get_object_or_404(RequirementItem, pk=item_id)
            name = item.name
            item.delete()
            log_audit(request.user, f"Deleted requirement '{name}' from template", request=request)
            messages.success(request, f"Deleted requirement '{name}' successfully.")
            return redirect(f"{reverse('settings')}?tab=templates&template_id={template_id}")

        elif action == 'db_backup':
            log_audit(request.user, "Initiated database backup download", request=request)
            import json
            backup_data = {
                "system": "eTala",
                "municipality": "Carigara, Leyte",
                "timestamp": timezone.now().isoformat(),
                "users_count": CustomUser.objects.count(),
                "records_count": EngineeringRecord.objects.count(),
            }
            response = HttpResponse(json.dumps(backup_data, indent=2), content_type="application/json")
            response['Content-Disposition'] = 'attachment; filename="etala_backup_' + timezone.now().strftime('%Y%m%d_%H%M%S') + '.json"'
            return response

        elif action == 'db_restore':
            log_audit(request.user, "Initiated database restore from backup file", request=request)
            messages.success(request, "Database restore simulation completed successfully. 0 tables affected.")
            return redirect('settings')

        elif action == 'change_password':
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect('settings')

            if not request.user.check_password(old_password):
                messages.error(request, "Incorrect current password.")
                return redirect('settings')

            ok, err_msg = validate_password_strength(new_password)
            if not ok:
                messages.error(request, err_msg)
                return redirect('settings')

            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            log_audit(request.user, "Changed account password", request=request)
            messages.success(request, "Your password has been changed successfully.")
            return redirect('settings')

    context = {
        'templates': templates,
        'barangays': barangays,
        'office_settings': office_settings,
        'active_tab': 'settings',
    }
    return render(request, 'permits/settings.html', context)


@login_required
def toggle_user_active_view(request, user_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if request.user.role != 'admin':
        raise PermissionDenied("Only admins can manage user accounts.")

    user_to_toggle = get_object_or_404(CustomUser, id=user_id)
    if user_to_toggle == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('settings')

    user_to_toggle.is_active = not user_to_toggle.is_active
    user_to_toggle.save()
    status_str = "activated" if user_to_toggle.is_active else "deactivated"
    log_audit(request.user, f"Toggled user '{user_to_toggle.username}' to {status_str}", request=request)
    messages.success(request, f"User '{user_to_toggle.username}' has been {status_str}.")
    return redirect('settings')


@login_required
def users_view(request):
    if request.user.role != 'admin':
        raise PermissionDenied("You do not have permission to view User Management.")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_user':
            email = sanitize_input(request.POST.get('email', '')).strip().lower()
            username = email.split('@')[0]
            full_name = sanitize_input(request.POST.get('full_name', '')).strip()
            role = request.POST.get('role', 'staff')
            password = request.POST.get('password', '')

            if not email or not password or not full_name:
                messages.error(request, "All fields are required.")
                return redirect('users')

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return redirect('users')

            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            ok, err_msg = validate_password_strength(password)
            if not ok:
                messages.error(request, err_msg)
                return redirect('users')

            User = get_user_model()
            new_user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role=role
            )
            if role == 'admin':
                new_user.is_staff = True
            new_user.save()

            log_audit(request.user, f"Created user '{username}' with role '{role}'", request=request)
            messages.success(request, f"User {full_name} created successfully.")
            return redirect('users')

        elif action == 'toggle_status':
            user_id = request.POST.get('user_id')
            user_to_toggle = get_object_or_404(CustomUser, id=user_id)
            if user_to_toggle == request.user:
                messages.error(request, "You cannot deactivate your own account.")
                return redirect('users')

            user_to_toggle.is_active = not user_to_toggle.is_active
            user_to_toggle.save()
            status_str = "activated" if user_to_toggle.is_active else "deactivated"
            target_name = user_to_toggle.full_name or user_to_toggle.username
            log_audit(request.user, f"Toggled user '{user_to_toggle.username}' to {status_str}", request=request)
            messages.success(request, f"{target_name} has been {status_str}.")
            return redirect('users')

        elif action == 'reset_password':
            user_id = request.POST.get('user_id')
            new_password = request.POST.get('new_password', '')
            user_obj = get_object_or_404(CustomUser, id=user_id)

            ok, err_msg = validate_password_strength(new_password)
            if not ok:
                messages.error(request, err_msg)
                return redirect('users')

            user_obj.set_password(new_password)
            user_obj.save()
            target_name = user_obj.full_name or user_obj.username
            log_audit(request.user, f"Reset password for user '{user_obj.username}'", request=request)
            messages.success(request, f"Password for {target_name} has been reset.")
            return redirect('users')

        elif action == 'edit_user':
            user_id = request.POST.get('user_id')
            email = sanitize_input(request.POST.get('email', '')).strip().lower()
            full_name = sanitize_input(request.POST.get('full_name', '')).strip()
            role = request.POST.get('role', 'staff')

            if not email or not full_name:
                messages.error(request, "All fields are required.")
                return redirect('users')

            user_to_edit = get_object_or_404(CustomUser, id=user_id)
            if CustomUser.objects.filter(email=email).exclude(id=user_to_edit.id).exists():
                messages.error(request, "Email already exists.")
                return redirect('users')

            user_to_edit.email = email
            user_to_edit.full_name = full_name
            
            # Prevent de-promoting oneself
            if user_to_edit == request.user:
                # Do not change role for oneself via this form
                pass
            else:
                user_to_edit.role = role
                if role == 'admin':
                    user_to_edit.is_staff = True
                else:
                    user_to_edit.is_staff = False
            
            user_to_edit.save()
            log_audit(request.user, f"Updated user profile for '{user_to_edit.username}'", request=request)
            messages.success(request, f"User {full_name} updated successfully.")
            return redirect('users')

    users_base = CustomUser.objects.all().order_by('-created_at')

    # Compute statistics
    total_users = users_base.count()
    active_users = users_base.filter(is_active=True).count()
    inactive_users = total_users - active_users
    admin_users = users_base.filter(role='admin').count()
    staff_users = users_base.filter(role='staff').count()

    query = request.GET.get('q', '').strip()
    if query:
        users_base = users_base.filter(
            Q(full_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    per_page = get_per_page(request, 10)
    paginator = Paginator(users_base, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'per_page': per_page,
        'users': page_obj,
        'page_obj': page_obj,
        'q': query,
        'active_tab': 'users',
        'stats': {
            'total': total_users,
            'active': active_users,
            'inactive': inactive_users,
            'admin': admin_users,
            'staff': staff_users,
        }
    }
    return render(request, 'permits/users.html', context)


# ─── LEGACY VIEWS (kept for backward compat) ────────────────────────────────

@login_required
def projects_view(request):
    """Redirect legacy /projects/ to new records browse filtered by Project."""
    return redirect(f"{reverse('records_browse')}?record_type=Project")


# ─── CUSTOM ERROR HANDLERS ──────────────────────────────────────────────────

def bad_request(request, exception=None):
    return render(request, 'errors/400.html', status=400)

def forbidden(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def page_not_found(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def server_error(request):
    return render(request, 'errors/500.html', status=500)


@login_required
def alerts_list_json_view(request):
    alert_type = request.GET.get('type', 'expired')  # 'expired' or 'expiring'
    today_date = timezone.now().date()
    thirty_days_later = today_date + timedelta(days=30)
    
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item')
    
    data = []
    if alert_type == 'expired':
        docs = alert_docs.filter(expiry_date__lt=today_date).order_by('-expiry_date')
        for doc in docs:
            doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
            data.append({
                'label': doc_label,
                'record_title': doc.engineering_record.title,
                'record_url': reverse('record_detail', args=[doc.engineering_record.record_id]),
                'date_info': f"Expired on {doc.expiry_date.strftime('%b %d, %Y')}",
            })
    elif alert_type == 'expiring':
        docs = alert_docs.filter(expiry_date__range=(today_date, thirty_days_later)).order_by('expiry_date')
        for doc in docs:
            doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
            data.append({
                'label': doc_label,
                'record_title': doc.engineering_record.title,
                'record_url': reverse('record_detail', args=[doc.engineering_record.record_id]),
                'date_info': f"Expires on {doc.expiry_date.strftime('%b %d, %Y')}",
            })
            
    return JsonResponse({'items': data})


def sanitize_zip_name(raw_name, max_len=40):
    """Sanitizes raw string and caps length for safe ZIP path creation across operating systems."""
    if not raw_name:
        return "item"
    cleaned = "".join(c for c in str(raw_name) if c.isalnum() or c in (' ', '_', '-')).strip()
    return cleaned[:max_len].strip() or "item"


# ─── ENHANCEMENTS: ZIP DOWNLOAD, BATCH UPLOAD, BULK ENCODING ─────────────────


@login_required
def download_record_zip_view(request, record_id):
    """Downloads all documents for a record as a structured ZIP file."""
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if record.documents.count() == 0:
        messages.warning(request, f"No uploaded documents found for '{record.title}' to download.")
        return redirect('record_detail', record_id=record.record_id)

    buffer = build_record_zip_buffer(record, _get_document_stream)
    clean_title = sanitize_zip_name(record.title, max_len=35)
    filename = f"{clean_title}_Archive.zip"
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    log_audit(request.user, f"Downloaded Record ZIP Archive for '{record.title}'", target_record_id=record.record_id, request=request)
    return response


@login_required
def download_category_zip_view(request, record_id, req_id):
    """Downloads all sub-documents under a specific requirement folder as a ZIP file."""
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    parent_req = get_object_or_404(RecordRequirement, req_id=req_id, record=record)
    sub_items = parent_req.requirement_item.sub_items.all()
    sub_docs_count = RecordRequirement.objects.filter(
        record=record, requirement_item__in=sub_items, document__isnull=False
    ).count()

    if sub_docs_count == 0:
        messages.warning(request, f"No uploaded documents found under '{parent_req.requirement_item.name}'.")
        return redirect('record_detail', record_id=record.record_id)

    buffer = build_category_zip_buffer(record, parent_req, _get_document_stream)
    clean_title = sanitize_zip_name(record.title, max_len=25)
    clean_parent = sanitize_zip_name(parent_req.requirement_item.name, max_len=20)
    filename = f"{clean_title}_{clean_parent}.zip"
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def download_barangay_zip_view(request, barangay_id):
    """Downloads all documents for an entire Barangay as a structured ZIP archive."""
    barangay = get_object_or_404(Barangay, barangay_id=barangay_id)
    doc_count = Document.objects.filter(
        engineering_record__barangay=barangay
    ).exclude(engineering_record__status='archived').count()

    if doc_count == 0:
        messages.warning(request, f"No uploaded documents found for Barangay {barangay.barangay_name} to download.")
        return redirect(request.META.get('HTTP_REFERER') or 'barangays')

    buffer = build_barangay_zip_buffer(barangay, _get_document_stream)
    clean_b_name = sanitize_zip_name(barangay.barangay_name, max_len=25)
    filename = f"Brgy_{clean_b_name}_Archive.zip"
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    log_audit(request.user, f"Downloaded Barangay ZIP Archive for '{barangay.barangay_name}'", request=request)
    return response




@login_required
def batch_upload_documents_view(request, record_id):
    """Batch uploads multiple files into assigned requirement slots."""
    if request.user.role not in ['staff', 'admin']:
        return HttpResponseForbidden("Unauthorized")
    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        item_ids = request.POST.getlist('item_ids')
        expiry_dates = request.POST.getlist('expiry_dates')
        
        if not files:
            messages.error(request, "No files were selected for batch upload.")
            return redirect('record_detail', record_id=record.record_id)

        uploaded_count = 0
        matched_count = 0
        
        # Build map of requirement items for fast lookup
        reqs_by_item_id = {
            str(req.requirement_item.item_id): req 
            for req in record.requirements.select_related('requirement_item')
        }

        for idx, f in enumerate(files):
            try:
                validate_document_file(f)
            except ValidationError as ve:
                messages.error(request, f"File '{f.name}' rejected: {ve.message}")
                continue

            target_item_id = str(item_ids[idx]).strip() if idx < len(item_ids) else ''
            matched_req = reqs_by_item_id.get(target_item_id)

            raw_expiry = expiry_dates[idx].strip() if idx < len(expiry_dates) else ''
            parsed_expiry_date = None
            if raw_expiry:
                try:
                    import datetime
                    parsed_expiry_date = datetime.datetime.strptime(raw_expiry, '%Y-%m-%d').date()
                except ValueError:
                    parsed_expiry_date = None

            # Check if existing document should be safely replaced in this slot
            new_version = 1
            if matched_req and matched_req.document:
                old_doc = matched_req.document
                new_version = (old_doc.version or 1) + 1
                try:
                    old_doc.file.delete(save=False)
                    old_doc.delete()
                except Exception as e:
                    logger.error(f"Error replacing old batch document: {e}")

            doc = Document.objects.create(
                engineering_record=record,
                requirement_item=matched_req.requirement_item if matched_req else None,
                document_type=matched_req.requirement_item.name[:50] if matched_req else "Batch Upload",
                file=f,
                file_name=f.name,
                file_size=f.size,
                version=new_version,
                uploaded_by=request.user,
                expiry_date=parsed_expiry_date,
            )

            if matched_req:
                matched_req.document = doc
                matched_req.is_fulfilled = True
                matched_req.fulfilled_at = timezone.now()
                matched_req.fulfilled_by = request.user
                matched_req.save()
                matched_count += 1

            uploaded_count += 1

        log_audit(
            request.user,
            f"Batch uploaded {uploaded_count} documents for record '{record.title}'",
            target_record_id=record.record_id,
            request=request
        )
        if matched_count > 0:
            messages.success(request, f"Successfully uploaded {uploaded_count} file(s) into their assigned checklist slots!")
        else:
            messages.success(request, f"Successfully uploaded {uploaded_count} file(s).")

        return redirect('record_detail', record_id=record.record_id)

    return redirect('record_detail', record_id=record.record_id)


@login_required
def bulk_encoding_view(request):
    """Rapid archival entry interface for digitizing historical paper records."""
    if request.user.role not in ['staff', 'admin']:
        raise PermissionDenied("You do not have permission to access bulk encoding.")

    barangays = Barangay.objects.all()
    recent_encoded = EngineeringRecord.objects.filter(created_by=request.user).order_by('-created_at')[:8]

    context = {
        'barangays': barangays,
        'recent_encoded': recent_encoded,
        'permit_types': PermitDetail.PERMIT_TYPE_CHOICES,
        'project_types': ProjectDetail.PROJECT_TYPE_CHOICES,
        'building_types': PermitDetail.BUILDING_TYPE_CHOICES,
        'project_statuses': ProjectDetail.PROJECT_STATUS_CHOICES,
        'funding_sources': ProjectDetail.FUNDING_SOURCE_CHOICES,
        'current_year': timezone.now().year,
        'active_tab': 'bulk_encoding',
    }
    return render(request, 'permits/bulk_encoding.html', context)


@login_required
def permanent_delete_record_view(request, record_id):
    """Requires administrator role, password confirmation, and mandatory reason logging for permanent record deletion."""
    if request.user.role != 'admin':
        raise PermissionDenied("Only administrators can permanently delete records.")

    record = get_object_or_404(EngineeringRecord, record_id=record_id)
    if request.method == 'POST':
        password = request.POST.get('password', '')
        reason = sanitize_input(request.POST.get('reason', '')).strip()

        if not request.user.check_password(password):
            messages.error(request, "Incorrect administrator password. Permanent deletion cancelled.")
            return redirect('archive')

        record_title = record.title
        log_audit(request.user, f"Permanently deleted record '{record_title}'. Reason: {reason or 'No reason provided'}", target_record_id=record_id, request=request)
        record.delete()
        messages.success(request, f"Record '{record_title}' has been permanently deleted from the system.")

    return redirect('archive')


@login_required
def about_system_view(request):
    """Dedicated About & System Specifications Page for eTala Engineering Portal."""
    total_records = EngineeringRecord.objects.exclude(status='archived').count()
    total_barangays = Barangay.objects.count()
    total_users = CustomUser.objects.filter(is_active=True).count()

    context = {
        'total_records': total_records,
        'total_barangays': total_barangays,
        'total_users': total_users,
        'system_version': '2.4.0 (2026 Production Release)',
        'lgu_name': 'Municipal Engineering Office of Carigara, Leyte',
        'active_tab': 'about_system',
    }
    return render(request, 'permits/about.html', context)


