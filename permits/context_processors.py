import datetime
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.core.cache import cache
from .models import AuditLog, Document, LoginAttempt, UserDevice

def recent_notifications(request):
    if not request.user.is_authenticated:
        return {'recent_notifications': [], 'notifications_count': 0, 'has_urgent_alerts': False}

    # Skip heavy DB context processor on static, media, or API requests
    if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/api/'):
        return {'recent_notifications': [], 'notifications_count': 0, 'has_urgent_alerts': False}

    cache_key = f"recent_notifications_{request.user.pk}_{request.user.role}_v2"
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    alerts = []
    
    # 1. Security failed login alert for admins (past 24 hours, localized Philippine time)
    if request.user.role == 'admin':
        twenty_four_hours_ago = timezone.now() - datetime.timedelta(hours=24)
        recent_failed = LoginAttempt.objects.filter(success=False, timestamp__gte=twenty_four_hours_ago).order_by('-timestamp')
        latest_failed = recent_failed.first()
        if latest_failed:
            failed_count = recent_failed.count()
            local_ts = timezone.localtime(latest_failed.timestamp)
            time_str = local_ts.strftime('%b %d, %Y • %I:%M %p')
            alert_action = f'{failed_count} recent failed login attempt(s) detected.'
            notif_id = f"sec_{latest_failed.pk}_{slugify(time_str)}"
            alerts.append({
                'id': notif_id,
                'type': 'security',
                'action': alert_action,
                'url': f"{reverse('activity_logs')}?tab=login&status=failed",
                'badge': 'Security',
                'time': time_str,
                'user': None,
                'username': None,
                'performed_at': latest_failed.timestamp,
            })

    # 2. Expiry tracking for documents (active window: 30 days before expiry and up to 30 days after expiry)
    today_date = timezone.now().date()
    thirty_days_later = today_date + datetime.timedelta(days=30)
    thirty_days_ago = today_date - datetime.timedelta(days=30)
    
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False,
        expiry_date__gte=thirty_days_ago,
        expiry_date__lte=thirty_days_later
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item').order_by('-uploaded_at', '-document_id')[:12]
    
    for doc in alert_docs:
        doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
        doc_id_slug = f"doc_{doc.document_id}_{doc.expiry_date.strftime('%Y%m%d')}"
        if doc.expiry_date < today_date:
            alerts.append({
                'id': doc_id_slug,
                'type': 'expired',
                'action': f'Expired: {doc_label} for "{doc.engineering_record.title}"',
                'url': f"{reverse('record_detail', args=[doc.engineering_record.record_id])}?highlight_doc={doc.document_id}&item_id={doc.requirement_item_id or ''}#doc-{doc.document_id}",
                'badge': 'expired',
                'time': f'Expired last {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': doc.uploaded_at,
            })
        elif doc.expiry_date <= thirty_days_later:
            alerts.append({
                'id': doc_id_slug,
                'type': 'expiring',
                'action': f'Expiring: {doc_label} for "{doc.engineering_record.title}"',
                'url': f"{reverse('record_detail', args=[doc.engineering_record.record_id])}?highlight_doc={doc.document_id}&item_id={doc.requirement_item_id or ''}#doc-{doc.document_id}",
                'badge': 'expiring',
                'time': f'Expires on {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': doc.uploaded_at,
            })

    # Fetch read/deleted notification IDs from database for cross-device sync
    user_actions = AuditLog.objects.filter(
        user=request.user, 
        action__startswith='NOTIF_'
    ).values_list('action', flat=True)
    
    read_ids = set()
    deleted_ids = set()
    for act in user_actions:
        if act.startswith('NOTIF_READ:'):
            read_ids.add(act[11:])
        elif act.startswith('NOTIF_DELETED:'):
            deleted_ids.add(act[14:])

    # Filter out deleted alerts and compute real-time unread count
    filtered_alerts = []
    unread_count = 0
    for a in alerts:
        notif_id = a.get('id') or f"{slugify(a['action'])}_{slugify(a['time'])}"
        a['id'] = notif_id
        if notif_id in deleted_ids:
            continue
        is_read = notif_id in read_ids
        a['is_read'] = is_read
        if not is_read:
            unread_count += 1
        filtered_alerts.append(a)

    result = {
        'recent_notifications': filtered_alerts[:8],
        'notifications_count': unread_count,
        'has_urgent_alerts': unread_count > 0,
    }
    # Cache for 10 seconds for real-time responsiveness
    cache.set(cache_key, result, timeout=10)
    return result


def system_global_context(request):
    """
    Globally injects dynamic system counts and statistics (e.g. total_barangays_count)
    across all templates in eTala, ensuring that adding or removing barangays automatically
    updates everywhere with zero hardcoding.
    """
    total_brgys = cache.get('global_total_barangays_count')
    if total_brgys is None:
        try:
            from .models import Barangay
            total_brgys = Barangay.objects.count()
            cache.set('global_total_barangays_count', total_brgys, timeout=60)
        except Exception:
            total_brgys = 49
    return {
        'total_barangays_count': total_brgys,
    }
