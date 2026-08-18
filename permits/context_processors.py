import datetime
from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache
from .models import AuditLog, Document, LoginAttempt

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
    
    # 1. Security failed login alert for admins (real-time query)
    if request.user.role == 'admin':
        latest_failed = LoginAttempt.objects.filter(success=False).order_by('-timestamp').first()
        if latest_failed:
            failed_count = LoginAttempt.objects.filter(success=False).count()
            time_str = latest_failed.timestamp.strftime('%b %d, %Y • %I:%M %p')
            alerts.append({
                'type': 'security',
                'action': f'{failed_count} failed login attempt(s) recorded.',
                'url': f"{reverse('activity_logs')}?tab=login&status=failed",
                'badge': 'Security',
                'time': time_str,
                'user': None,
                'username': None,
                'performed_at': latest_failed.timestamp,
            })

    # 2. Expiry tracking for documents (newest uploaded alerts appear at the top)
    today_date = timezone.now().date()
    thirty_days_later = today_date + datetime.timedelta(days=30)
    
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False,
        expiry_date__lte=thirty_days_later
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item').order_by('-uploaded_at', '-document_id')[:8]
    
    for doc in alert_docs:
        doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
        if doc.expiry_date < today_date:
            alerts.append({
                'type': 'expired',
                'action': f'Expired: {doc_label} for "{doc.engineering_record.title}"',
                'url': f"{reverse('record_detail', args=[doc.engineering_record.record_id])}?highlight_doc={doc.document_id}&item_id={doc.requirement_item_id or ''}#doc-{doc.document_id}",
                'badge': 'expired',
                'time': f'Expired on {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': doc.uploaded_at,
            })
        elif doc.expiry_date <= thirty_days_later:
            alerts.append({
                'type': 'expiring',
                'action': f'Expiring: {doc_label} for "{doc.engineering_record.title}"',
                'url': f"{reverse('record_detail', args=[doc.engineering_record.record_id])}?highlight_doc={doc.document_id}&item_id={doc.requirement_item_id or ''}#doc-{doc.document_id}",
                'badge': 'expiring',
                'time': f'Expires on {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': doc.uploaded_at,
            })

    result = {
        'recent_notifications': alerts[:8],
        'notifications_count': len(alerts),
        'has_urgent_alerts': len(alerts) > 0,
    }
    # Cache for 10 seconds for real-time responsiveness
    cache.set(cache_key, result, timeout=10)
    return result
