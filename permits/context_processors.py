import datetime
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.core.cache import cache
from django.db.models import Q
from .models import AuditLog, Document, LoginAttempt, UserDevice, EngineeringRecord

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
            alert_action = f'{failed_count} Failed Login Attempt{"s" if failed_count > 1 else ""}'
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

    # 3. Trash 30-day auto-purge warning alerts (records with <= 7 days left in Trash)
    now_dt = timezone.now()
    seven_days_warning_threshold = now_dt - datetime.timedelta(days=23)  # deleted between 23 and 30 days ago
    
    expiring_trash_records = EngineeringRecord.objects.filter(
        status='archived'
    ).filter(
        Q(deleted_at__lte=seven_days_warning_threshold) | (Q(deleted_at__isnull=True) & Q(updated_at__lte=seven_days_warning_threshold))
    ).order_by('deleted_at', 'updated_at')[:5]

    for tr in expiring_trash_records:
        days_left = tr.trash_days_remaining
        if days_left <= 7:
            trash_notif_id = f"trash_exp_{tr.record_id}_{days_left}d"
            alerts.append({
                'id': trash_notif_id,
                'type': 'trash_warning',
                'action': f"Trash Warning: '{tr.title}' will be permanently deleted in {days_left} day{'s' if days_left != 1 else ''}.",
                'url': f"{reverse('archive')}?q={tr.record_id}",
                'badge': 'Auto-Purge in 7d',
                'time': f"{days_left} day{'s' if days_left != 1 else ''} left to restore",
                'user': None,
                'username': None,
                'performed_at': tr.deleted_at or tr.updated_at,
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
    Globally injects dynamic system counts, statistics, and standard autocomplete suggestions
    for contractors and project titles across all templates in eTala.
    """
    total_brgys = cache.get('global_total_barangays_count')
    if total_brgys is None:
        try:
            from .models import Barangay
            total_brgys = Barangay.objects.count()
            cache.set('global_total_barangays_count', total_brgys, timeout=60)
        except Exception:
            total_brgys = 49

    common_project_titles = [
        "Concreting of Barangay Road",
        "Construction of Multi-Purpose Building",
        "Rehabilitation of Drainage Canal",
        "Installation of Solar Streetlights",
        "Construction of Evacuation Center",
        "Improvement of Barangay Health Center",
        "Construction of Day Care Center",
        "Rehabilitation of Flood Control Dike",
        "Construction of Perimeter Fence",
        "Repair and Maintenance of Municipal Hall",
        "Construction of Potable Water System (Level II)",
        "Improvement of Public Market Facilities",
    ]

    # Fetch unique active contractors from database cached for 60s
    contractor_list = cache.get('global_common_contractors')
    if contractor_list is None:
        try:
            from .models import ProjectDetail
            db_contractors = list(ProjectDetail.objects.exclude(contractor__isnull=True).exclude(contractor='').values_list('contractor', flat=True).distinct()[:15])
            base_contractors = [
                "By Administration (LGU Carigara)",
                "DPWH 2nd Leyte Engineering District",
                "Provincial Engineering Office (PEO Leyte)",
                "LGU Maintenance & Construction Team",
            ]
            combined = []
            for c in base_contractors + db_contractors:
                c_clean = c.strip()
                if c_clean and c_clean not in combined:
                    combined.append(c_clean)
            contractor_list = combined
            cache.set('global_common_contractors', contractor_list, timeout=60)
        except Exception:
            contractor_list = [
                "By Administration (LGU Carigara)",
                "DPWH 2nd Leyte Engineering District",
                "Provincial Engineering Office (PEO Leyte)",
            ]

    return {
        'total_barangays_count': total_brgys,
        'common_project_titles': common_project_titles,
        'common_contractors': contractor_list,
    }

