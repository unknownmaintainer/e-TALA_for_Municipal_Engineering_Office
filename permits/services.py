import csv
import datetime
from datetime import timedelta
import io
import json
import logging
import os
import zipfile

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import EngineeringRecord, RecordRequirement, AuditLog, LoginAttempt

logger = logging.getLogger('permits')


# ─── OFFICE SETTINGS PERSISTENCE SERVICE ───────────────────────────────────────

def get_office_settings():
    """Reads office configuration settings from JSON file with fallback defaults."""
    settings_path = os.path.join(settings.BASE_DIR, 'office_settings.json')
    defaults = {
        'office_name': 'Municipal Engineering Office',
        'municipality': 'Carigara',
        'province': 'Leyte'
    }
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                defaults.update(data)
        except Exception as exc:
            logger.error(f"Error reading office_settings.json: {exc}")
    return defaults


def save_office_settings(office_name, municipality, province):
    """Saves office configuration settings to JSON file."""
    settings_path = os.path.join(settings.BASE_DIR, 'office_settings.json')
    data = {
        'office_name': office_name,
        'municipality': municipality,
        'province': province
    }
    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as exc:
        logger.error(f"Error writing office_settings.json: {exc}")
        return False


# ─── RECORD ZIP ARCHIVE GENERATION SERVICE ───────────────────────────────────

def sanitize_zip_name(raw_name, max_len=40):
    """Sanitizes raw string and caps length for safe ZIP path creation across operating systems."""
    if not raw_name:
        return "item"
    cleaned = "".join(c for c in str(raw_name) if c.isalnum() or c in (' ', '_', '-')).strip()
    return cleaned[:max_len].strip() or "item"


def sanitize_file_name(raw_filename, max_name_len=35):
    """Sanitizes filename and extension, keeping total file name compact."""
    if not raw_filename:
        return "document"
    name_part, ext_part = os.path.splitext(os.path.basename(str(raw_filename)))
    clean_name = "".join(c for c in name_part if c.isalnum() or c in (' ', '_', '-')).strip()[:max_name_len].strip() or "doc"
    clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip()
    return f"{clean_name}{clean_ext}"


def build_record_zip_buffer(record, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all fulfilled documents for an EngineeringRecord.
    Organizes files by requirement checklist slots and folders with compact path limits.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        requirements = record.requirements.select_related('requirement_item', 'document')
        for req in requirements:
            if req.document:
                try:
                    file_obj, _, _ = stream_getter_func(req.document)
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                        
                        item = req.requirement_item
                        clean_doc_fname = sanitize_file_name(req.document.file_name or 'document', max_name_len=35)
                        if item and item.parent:
                            parent_folder = sanitize_zip_name(item.parent.name, max_len=30)
                            item_name = sanitize_zip_name(item.name, max_len=25)
                            folder_path = f"{parent_folder}/{item_name}_{clean_doc_fname}"
                        elif item:
                            item_name = sanitize_zip_name(item.name, max_len=30)
                            folder_path = f"{item_name}/{clean_doc_fname}"
                        else:
                            folder_path = f"Documents/{clean_doc_fname}"
                        
                        zip_file.writestr(folder_path, file_data)
                except Exception as exc:
                    logger.error(f"Error zipping document {req.document.document_id}: {exc}")

        other_docs = record.documents.filter(requirement_item__isnull=True)
        for doc in other_docs:
            try:
                file_obj, _, _ = stream_getter_func(doc)
                if file_obj:
                    file_data = file_obj.read()
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                    clean_doc_fname = sanitize_file_name(doc.file_name or 'document', max_name_len=35)
                    zip_file.writestr(f"Other_Documents/{clean_doc_fname}", file_data)
            except Exception as exc:
                logger.error(f"Error zipping document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_category_zip_buffer(record, parent_req, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all documents under a specific requirement parent category.
    """
    parent_item = parent_req.requirement_item
    sub_items = parent_item.sub_items.all()
    sub_reqs = RecordRequirement.objects.filter(record=record, requirement_item__in=sub_items).select_related('requirement_item', 'document')
    
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for req in sub_reqs:
            if req.document:
                try:
                    file_obj, _, _ = stream_getter_func(req.document)
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                        parent_name = sanitize_zip_name(parent_item.name, max_len=30)
                        item_name = sanitize_zip_name(req.requirement_item.name, max_len=25)
                        clean_doc_fname = sanitize_file_name(req.document.file_name or 'document', max_name_len=35)
                        zip_file.writestr(f"{parent_name}/{item_name}_{clean_doc_fname}", file_data)
                except Exception as exc:
                    logger.error(f"Error zipping sub-document {req.document.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_barangay_zip_buffer(barangay, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all documents for an entire Barangay.
    Organizes files into structured folders by Permits and Projects with compact path limits.
    """
    buffer = io.BytesIO()
    records = EngineeringRecord.objects.filter(barangay=barangay).exclude(status='archived').prefetch_related('documents')
    
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for record in records:
            clean_record_title = sanitize_zip_name(record.title, max_len=40)
            section = "Permits" if record.record_type == 'Permit' else "Projects"
            
            for doc in record.documents.all():
                try:
                    file_obj, _, _ = stream_getter_func(doc)
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                        
                        clean_b_name = sanitize_zip_name(barangay.barangay_name, max_len=25)
                        clean_doc_fname = sanitize_file_name(doc.file_name or (doc.file.name if doc.file else 'document'), max_name_len=35)
                        folder_path = f"{clean_b_name}_Archive/{section}/{clean_record_title}/{clean_doc_fname}"
                        zip_file.writestr(folder_path, file_data)

                except Exception as exc:
                    logger.error(f"Error zipping barangay document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer



def send_document_expiry_alerts():
    """
    Scans all active documents with an expiry_date within 30 days or already expired,
    and sends a formatted HTML email summary to staff & admin users.
    """
    from django.core.mail import send_mail
    from django.contrib.auth import get_user_model
    
    today_date = timezone.now().date()
    thirty_days_later = today_date + timedelta(days=30)
    
    from .models import Document
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item')
    
    expired_docs = alert_docs.filter(expiry_date__lt=today_date).order_by('-expiry_date')
    expiring_docs = alert_docs.filter(expiry_date__range=(today_date, thirty_days_later)).order_by('expiry_date')
    
    if not expired_docs.exists() and not expiring_docs.exists():
        return False, "No expired or expiring documents found."
        
    User = get_user_model()
    recipients = list(User.objects.filter(is_active=True, role__in=['admin', 'staff']).values_list('email', flat=True))
    if not recipients:
        return False, "No active admin/staff email recipients found."

    expired_items = "".join([f"<li><strong>{d.requirement_item.name if d.requirement_item else d.document_type}</strong> — {d.engineering_record.title} (Expired: {d.expiry_date.strftime('%b %d, %Y')})</li>" for d in expired_docs[:10]])
    expiring_items = "".join([f"<li><strong>{d.requirement_item.name if d.requirement_item else d.document_type}</strong> — {d.engineering_record.title} (Expires: {d.expiry_date.strftime('%b %d, %Y')})</li>" for d in expiring_docs[:10]])

    expired_section = f"<h3 style='color:#b91c1c; font-size:14px; margin:16px 0 8px 0;'>🚨 Expired Documents ({expired_docs.count()})</h3><ul style='padding-left:20px; color:#475569; font-size:13px;'>{expired_items}</ul>" if expired_docs.exists() else ""
    expiring_section = f"<h3 style='color:#b45309; font-size:14px; margin:16px 0 8px 0;'>⚠️ Expiring Soon (&lt; 30 Days) ({expiring_docs.count()})</h3><ul style='padding-left:20px; color:#475569; font-size:13px;'>{expiring_items}</ul>" if expiring_docs.exists() else ""

    html_message = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #002855 0%, #001f42 100%); padding: 24px 28px; text-align: center;">
            <h1 style="color: #ffffff; font-size: 20px; margin: 0; font-weight: 700;">eTala Alert System</h1>
            <p style="color: #C5A059; font-size: 11px; margin: 4px 0 0 0; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 600;">Municipal Engineering Office &bull; Carigara, Leyte</p>
        </div>
        <div style="padding: 24px 28px;">
            <h2 style="color: #0f172a; font-size: 16px; margin: 0 0 12px 0;">Document Expiry Alert Summary</h2>
            <p style="color: #475569; font-size: 14px; margin: 0 0 20px 0;">
                The following engineering record documents require immediate administrative attention:
            </p>
            {expired_section}
            {expiring_section}
        </div>
        <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px 28px; text-align: center;">
            <p style="color: #94a3b8; font-size: 11px; margin: 0;">eTala Municipal Engineering Office &bull; Carigara, Leyte</p>
        </div>
    </div>
    """

    send_mail(
        subject='eTala Alert: Document Expiry Summary Notice',
        message=f'eTala Document Expiry Alert Summary: {expired_docs.count()} expired, {expiring_docs.count()} expiring soon.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        html_message=html_message,
        fail_silently=False,
    )

    return True, f"Sent email notifications to {len(recipients)} staff/admin user(s) ({expired_docs.count()} expired, {expiring_docs.count()} expiring soon)."



# ─── ACTIVITY LOGS CSV EXPORT SERVICE ─────────────────────────────────────────

def build_activity_logs_csv_rows(tab, query, date_filter, action_type, current_user):
    """
    Generates formatted row data tuples for exporting LoginAttempts or AuditLogs as CSV.
    """
    now = timezone.now()
    if tab == 'login' and current_user.role == 'admin':
        qs = LoginAttempt.objects.all().order_by('-timestamp')
        if date_filter == '24h':
            qs = qs.filter(timestamp__gte=now - timedelta(hours=24))
        elif date_filter == '7d':
            qs = qs.filter(timestamp__gte=now - timedelta(days=7))
        elif date_filter == '30d':
            qs = qs.filter(timestamp__gte=now - timedelta(days=30))
            
        if action_type == 'success':
            qs = qs.filter(success=True)
        elif action_type == 'failed':
            qs = qs.filter(success=False)
            
        if query:
            qs = qs.filter(Q(email_attempted__icontains=query) | Q(ip_address__icontains=query))
            
        headers = ['Log ID', 'Email Attempted', 'Status', 'IP Address', 'Timestamp (PST)']
        def row_generator():
            yield headers
            for item in qs:
                yield [
                    item.id,
                    item.email_attempted,
                    "Success" if item.success else "Failed",
                    item.ip_address or "N/A",
                    item.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                ]
        return f"eTala_Login_Attempts_{now.strftime('%Y%m%d')}.csv", row_generator()
    else:
        qs = AuditLog.objects.all().select_related('user').order_by('-performed_at')
        if current_user.role != 'admin':
            qs = qs.filter(user=current_user)
            
        if date_filter == '24h':
            qs = qs.filter(performed_at__gte=now - timedelta(hours=24))
        elif date_filter == '7d':
            qs = qs.filter(performed_at__gte=now - timedelta(days=7))
        elif date_filter == '30d':
            qs = qs.filter(performed_at__gte=now - timedelta(days=30))
            
        if query:
            qs = qs.filter(Q(action__icontains=query) | Q(user__username__icontains=query) | Q(user__full_name__icontains=query))
            
        headers = ['Log ID', 'User / Operator', 'Role', 'Action Executed', 'Target Record ID', 'IP Address', 'Timestamp (PST)']
        def row_generator():
            yield headers
            for item in qs:
                if item.user:
                    user_str = item.user.full_name or item.user.username
                    role_str = item.user.get_role_display()
                else:
                    user_str = "System"
                    role_str = "System"
                yield [
                    item.log_id,
                    user_str,
                    role_str,
                    item.action,
                    item.target_record_id or "N/A",
                    item.ip_address or "N/A",
                    item.performed_at.strftime("%Y-%m-%d %H:%M:%S")
                ]
        return f"eTala_Audit_Trail_{now.strftime('%Y%m%d')}.csv", row_generator()


# ─── REUSABLE RECORD FILTER SERVICE ──────────────────────────────────────────

def filter_engineering_records(base_qs, query='', record_type='', project_scope='', barangay_id='', status='', year='', permit_type='', project_type='', illegal_filter=''):
    """
    Applies common search and filter criteria to an EngineeringRecord QuerySet.
    """
    qs = base_qs
    if query:
        search_filter = (
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(barangay__barangay_name__icontains=query) |
            Q(permit_detail__permit_number__icontains=query) |
            Q(permit_detail__applicant_name__icontains=query) |
            Q(permit_detail__permit_type__icontains=query) |
            Q(permit_detail__building_type__icontains=query) |
            Q(project_detail__project_type__icontains=query) |
            Q(project_detail__contractor__icontains=query) |
            Q(project_detail__funding_source__icontains=query) |
            Q(record_type__icontains=query) |
            Q(project_scope__icontains=query) |
            Q(illegal_compliance_status__icontains=query) |
            Q(status__icontains=query) |
            Q(created_by__full_name__icontains=query) |
            Q(created_by__username__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(year=int(query)) | Q(created_at__year=int(query)) | Q(date_started__year=int(query))
        qs = qs.filter(search_filter).distinct()

    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)
    if status:
        qs = qs.filter(status=status)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except (ValueError, TypeError):
            qs = qs.filter(year=year)
    if permit_type:
        qs = qs.filter(permit_detail__permit_type=permit_type)
    if project_type:
        qs = qs.filter(project_detail__project_type=project_type)

    if illegal_filter in ['1', 'true'] or record_type == 'Illegal':
        qs = qs.filter(is_illegal_construction=True)
    elif illegal_filter in ['unresolved', 'pending_permit', 'resolved']:
        qs = qs.filter(is_illegal_construction=True, illegal_compliance_status=illegal_filter)

    return qs
