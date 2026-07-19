import datetime
from django.utils import timezone
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import AuditLog, Document, LoginAttempt

def recent_notifications(request):
    if request.user.is_authenticated:
        # Gather active system-wide warning/alert items (only most important events)
        alerts = []
        
        # Security failed login alert for admins
        if request.user.role == 'admin':
            failed_logins = LoginAttempt.objects.filter(success=False).count()
            if failed_logins > 0:
                alerts.append({
                    'type': 'security',
                    'action': f'{failed_logins} failed login attempt(s) recorded.',
                    'url': f"{reverse('settings')}?tab=logs&status=failed",
                    'badge': 'security',
                    'time': None,
                    'user': None,
                    'username': None,
                    'performed_at': None,
                })
        
        # Expiry tracking for documents
        today_date = timezone.now().date()
        thirty_days_later = today_date + datetime.timedelta(days=30)
        
        alert_docs = Document.objects.filter(
            expiry_date__isnull=False
        ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item')
        
        expired_docs = alert_docs.filter(expiry_date__lt=today_date)
        for doc in expired_docs:
            doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
            alerts.append({
                'type': 'expired',
                'action': f'Expired: {doc_label} for "{doc.engineering_record.title}"',
                'url': reverse('record_detail', args=[doc.engineering_record.record_id]),
                'badge': 'expired',
                'time': f'Expired on {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': None,
            })
            
        expiring_docs = alert_docs.filter(expiry_date__range=(today_date, thirty_days_later))
        for doc in expiring_docs:
            doc_label = doc.requirement_item.name if doc.requirement_item else doc.document_type
            alerts.append({
                'type': 'expiring',
                'action': f'Expiring: {doc_label} for "{doc.engineering_record.title}"',
                'url': reverse('record_detail', args=[doc.engineering_record.record_id]),
                'badge': 'expiring',
                'time': f'Expires on {doc.expiry_date.strftime("%b %d, %Y")}',
                'user': None,
                'username': None,
                'performed_at': None,
            })
            
        return {
            'recent_notifications': alerts,
            'notifications_count': len(alerts),
            'has_urgent_alerts': len(alerts) > 0,
        }
        
    return {
        'recent_notifications': [],
        'notifications_count': 0,
        'has_urgent_alerts': False,
    }
