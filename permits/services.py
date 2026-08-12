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

def build_record_zip_buffer(record, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all fulfilled documents for an EngineeringRecord.
    Organizes files by requirement checklist slots and folders.
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
                        doc_fname = req.document.file_name or 'document'
                        if item and item.parent:
                            folder_path = f"{item.parent.name}/{item.name}_{doc_fname}"
                        elif item:
                            folder_path = f"{item.name}/{doc_fname}"
                        else:
                            folder_path = f"Documents/{doc_fname}"
                        
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
                    doc_fname = doc.file_name or 'document'
                    zip_file.writestr(f"Other_Documents/{doc_fname}", file_data)
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
                        doc_fname = req.document.file_name or 'document'
                        zip_file.writestr(f"{parent_item.name}/{req.requirement_item.name}_{doc_fname}", file_data)
                except Exception as exc:
                    logger.error(f"Error zipping sub-document {req.document.document_id}: {exc}")

    buffer.seek(0)
    return buffer


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
