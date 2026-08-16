import csv
import datetime
from datetime import timedelta
import io
import json
import logging
import os
import zipfile

from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import EngineeringRecord, RecordRequirement, AuditLog, LoginAttempt

logger = logging.getLogger('permits')


def parse_decimal_safely(raw_val, max_digits=14, decimal_places=2):
    """Safely converts string/number to Decimal, handling commas, Philippine Peso symbols (₱, PHP, Php), exponents, and max digits."""
    if raw_val is None or raw_val == '':
        return None
    val_str = str(raw_val).replace(',', '').replace('₱', '').replace('PHP', '').replace('Php', '').replace('php', '').strip()
    if not val_str:
        return None
    try:
        dec = Decimal(val_str)
        if dec.is_nan() or dec.is_infinite():
            return None
        max_allowed = (Decimal(10) ** (max_digits - decimal_places)) - Decimal('0.01')
        if dec > max_allowed:
            dec = max_allowed
        elif dec < -max_allowed:
            dec = -max_allowed
        return dec.quantize(Decimal(10) ** -decimal_places)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None


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


def get_record_export_name(record, include_location=False):
    """
    Generates an ultra-clear, descriptive, and human-readable folder/file name for record exports.
    Tells the user:
      1. KANINO (Applicant / Owner / Violator / Contractor)
      2. ANO (Permit Type / Project Scope / Stop Order)
      3. REFERENCE/WHEN (Permit #, Year)
      4. SAAN (Barangay, when requested)
      
    Examples:
      - Juan_Dela_Cruz_Building_Permit_BP-2023-014
      - Road_Concreting_Sitio_Baybay_Infra_Project_2024
      - Unpermitted_Commercial_Building_Stop_Order_Brgy_Barugohay
      - Violation_Mardion_Fuerte_Stop_Order
    """
    # 1. ILLEGAL CONSTRUCTIONS & STOP ORDERS
    if record.is_illegal_construction:
        violator = ""
        if hasattr(record, 'permit_detail') and record.permit_detail and record.permit_detail.applicant_name:
            app = record.permit_detail.applicant_name.strip()
            if app.lower() not in ['n/a', 'none', '—', '', 'unknown', 'null']:
                violator = sanitize_zip_name(app, max_len=30).replace(" ", "_")
        
        raw_title = (record.title or "").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=35).replace(" ", "_") if raw_title else ""
        
        if violator and clean_title and violator.lower() != clean_title.lower():
            name_part = f"{violator}_{clean_title}"
        elif violator:
            name_part = f"Violation_{violator}"
        elif clean_title:
            name_part = clean_title
        else:
            name_part = "Illegal_Construction"
            
        status_suffix = "Stop_Order"
        if record.illegal_compliance_status == 'resolved':
            status_suffix = "Regularized_Permit"
        elif record.illegal_compliance_status == 'pending_permit':
            status_suffix = "Permit_Filed_Violation"
            
        if status_suffix.lower() in name_part.lower():
            record_slug = name_part
        else:
            record_slug = f"{name_part}_{status_suffix}"
            
        if include_location and record.barangay:
            b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=25).replace(" ", "_")
            record_slug = f"{record_slug}_Brgy_{b_name}"
            
        return record_slug

    # 2. STANDARD PERMITS
    elif record.record_type == 'Permit':
        applicant = ""
        permit_num = ""
        if hasattr(record, 'permit_detail') and record.permit_detail:
            app = record.permit_detail.applicant_name.strip()
            if app.lower() not in ['n/a', 'none', '—', '', 'unknown', 'null']:
                applicant = sanitize_zip_name(app, max_len=35).replace(" ", "_")
            pnum = record.permit_detail.permit_number.strip()
            if pnum and pnum.lower() not in ['n/a', 'none', '—', '', 'pending', 'null']:
                permit_num = sanitize_zip_name(pnum, max_len=25).replace(" ", "_")
                
        raw_title = (record.title or "").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=35).replace(" ", "_") if raw_title else ""
        
        if applicant:
            primary_name = applicant
        elif clean_title:
            primary_name = clean_title
        else:
            primary_name = "Permit"
            
        permit_type = record.specific_type_label or "Building_Permit"
        clean_type = sanitize_zip_name(permit_type, max_len=25).replace(" ", "_")
        
        if clean_type.lower() in primary_name.lower():
            base_slug = primary_name
        else:
            base_slug = f"{primary_name}_{clean_type}"
            
        # Add Permit # or Year if available
        if permit_num and permit_num.lower() not in base_slug.lower():
            base_slug = f"{base_slug}_{permit_num}"
        elif record.year and str(record.year) not in base_slug:
            base_slug = f"{base_slug}_{record.year}"
            
        if include_location and record.barangay:
            b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=25).replace(" ", "_")
            base_slug = f"{base_slug}_Brgy_{b_name}"
            
        return base_slug

    # 3. INFRASTRUCTURE PROJECTS
    else:
        raw_title = (record.title or "Infra_Project").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=38).replace(" ", "_")
        proj_type = record.specific_type_label or "Infra_Project"
        clean_proj_type = sanitize_zip_name(proj_type, max_len=25).replace(" ", "_")
        
        if clean_proj_type.lower() in clean_title.lower():
            base_slug = clean_title
        else:
            base_slug = f"{clean_title}_{clean_proj_type}"
            
        if hasattr(record, 'project_detail') and record.project_detail and record.project_detail.contractor:
            contractor = sanitize_zip_name(record.project_detail.contractor.strip(), max_len=25).replace(" ", "_")
            if contractor and contractor.lower() not in base_slug.lower() and contractor.lower() not in ['n/a', 'none', '—', 'null']:
                base_slug = f"{base_slug}_{contractor}"
                
        if record.year and str(record.year) not in base_slug:
            base_slug = f"{base_slug}_{record.year}"
            
        if include_location and record.barangay:
            b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=25).replace(" ", "_")
            base_slug = f"{base_slug}_Brgy_{b_name}"
            
        return base_slug


def build_record_zip_buffer(record, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all fulfilled documents for an EngineeringRecord.
    Organizes dropdown items into their parent folder, and standalone items directly in the record.
    """
    buffer = io.BytesIO()
    root_folder = get_record_export_name(record)
    used_paths = set()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for doc in record.documents.select_related('requirement_item', 'requirement_item__parent'):
            try:
                file_obj, _, _ = stream_getter_func(doc)
                if file_obj:
                    file_data = file_obj.read()
                    if hasattr(file_obj, 'close'):
                        file_obj.close()

                    raw_fname = doc.file_name or (doc.file.name if doc.file else 'document')
                    _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                    clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'

                    req_item = doc.requirement_item
                    if req_item and req_item.parent:
                        parent_folder = sanitize_zip_name(req_item.parent.name, max_len=35).replace(" ", "_")
                        item_file_name = sanitize_zip_name(req_item.name, max_len=45).replace(" ", "_") + clean_ext
                        folder_path = f"{root_folder}/{parent_folder}/{item_file_name}"
                    elif req_item:
                        item_file_name = sanitize_zip_name(req_item.name, max_len=45).replace(" ", "_") + clean_ext
                        folder_path = f"{root_folder}/{item_file_name}"
                    else:
                        clean_doc_fname = sanitize_file_name(raw_fname, max_name_len=40).replace(" ", "_")
                        folder_path = f"{root_folder}/Attachments/{clean_doc_fname}"

                    # Prevent duplicate zip internal path collisions
                    orig_path = folder_path
                    counter = 2
                    while folder_path in used_paths:
                        base_p, ext_p = os.path.splitext(orig_path)
                        folder_path = f"{base_p}_{counter}{ext_p}"
                        counter += 1
                    used_paths.add(folder_path)

                    zip_file.writestr(folder_path, file_data)
            except Exception as exc:
                logger.error(f"Error zipping record document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_category_zip_buffer(record, parent_req, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all documents under a specific requirement parent category.
    Organizes files cleanly into [Category_Name]/ with crystal-clear filenames.
    """
    parent_item = parent_req.requirement_item
    sub_items = list(parent_item.sub_items.all())
    
    sub_reqs = RecordRequirement.objects.filter(
        record=record, requirement_item__in=sub_items
    ).select_related('requirement_item', 'document')
    
    buffer = io.BytesIO()
    clean_parent = sanitize_zip_name(parent_item.name, max_len=45).replace(" ", "_")
    root_folder = clean_parent
    used_paths = set()
    processed_doc_ids = set()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for req in sub_reqs:
            if req.document and req.document.document_id not in processed_doc_ids:
                try:
                    file_obj, _, _ = stream_getter_func(req.document)
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                        raw_fname = req.document.file_name or (req.document.file.name if req.document.file else 'document')
                        _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                        clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'
                        item_file_name = sanitize_zip_name(req.requirement_item.name, max_len=45).replace(" ", "_") + clean_ext
                        folder_path = f"{root_folder}/{item_file_name}"

                        orig_path = folder_path
                        counter = 2
                        while folder_path in used_paths:
                            base_p, ext_p = os.path.splitext(orig_path)
                            folder_path = f"{base_p}_{counter}{ext_p}"
                            counter += 1
                        used_paths.add(folder_path)
                        processed_doc_ids.add(req.document.document_id)

                        zip_file.writestr(folder_path, file_data)
                except Exception as exc:
                    logger.error(f"Error zipping sub-document {req.document.document_id}: {exc}")

        # Also include any direct Document objects attached under these sub_items or parent_item
        direct_docs = Document.objects.filter(
            engineering_record=record,
            requirement_item__in=(sub_items + [parent_item])
        ).exclude(document_id__in=processed_doc_ids)

        for doc in direct_docs:
            try:
                file_obj, _, _ = stream_getter_func(doc)
                if file_obj:
                    file_data = file_obj.read()
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                    raw_fname = doc.file_name or (doc.file.name if doc.file else 'document')
                    clean_doc_fname = sanitize_file_name(raw_fname, max_name_len=45).replace(" ", "_")
                    folder_path = f"{root_folder}/{clean_doc_fname}"

                    orig_path = folder_path
                    counter = 2
                    while folder_path in used_paths:
                        base_p, ext_p = os.path.splitext(orig_path)
                        folder_path = f"{base_p}_{counter}{ext_p}"
                        counter += 1
                    used_paths.add(folder_path)
                    processed_doc_ids.add(doc.document_id)

                    zip_file.writestr(folder_path, file_data)
            except Exception as exc:
                logger.error(f"Error zipping direct document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_barangay_zip_buffer(barangay, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all documents for an entire Barangay.
    Organizes files cleanly into:
      Brgy_[Name]/
        ├── 01_Building_and_Ancillary_Permits/
        ├── 02_Infrastructure_Projects/
        └── 03_Illegal_Constructions_and_Stop_Orders/
    Guarantees zero file loss and crystal-clear record folder naming.
    """
    buffer = io.BytesIO()
    clean_b_name = sanitize_zip_name(barangay.barangay_name, max_len=30).replace(" ", "_")
    records = EngineeringRecord.objects.filter(barangay=barangay).exclude(status='archived').prefetch_related(
        'documents__requirement_item__parent'
    )
    
    used_record_folders = {}
    assigned_folders = set()
    used_paths = set()

    # Pre-assign unique and crystal-clear folder names to each record
    for record in records:
        base_name = get_record_export_name(record)
        unique_name = base_name
        if unique_name in assigned_folders:
            # If multiple records share the exact same title/applicant, add Case / Record ID for crystal clarity
            suffix_label = f"Case-{record.record_id}" if record.is_illegal_construction else f"Rec-{record.record_id}"
            unique_name = f"{base_name}_{suffix_label}"
            counter = 2
            while unique_name in assigned_folders:
                unique_name = f"{base_name}_{suffix_label}_{counter}"
                counter += 1
        assigned_folders.add(unique_name)
        used_record_folders[record.record_id] = unique_name

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for record in records:
            record_folder = used_record_folders.get(record.record_id, get_record_export_name(record))
            if record.is_illegal_construction:
                section = "03_Illegal_Constructions_and_Stop_Orders"
            elif record.record_type == 'Permit':
                section = "01_Building_and_Ancillary_Permits"
            else:
                section = "02_Infrastructure_Projects"
            
            for doc in record.documents.all():
                try:
                    file_obj, _, _ = stream_getter_func(doc)
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()
                        
                        raw_fname = doc.file_name or (doc.file.name if doc.file else 'document')
                        _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                        clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'
                        req_item = doc.requirement_item

                        if req_item and req_item.parent:
                            parent_folder = sanitize_zip_name(req_item.parent.name, max_len=35).replace(" ", "_")
                            item_file_name = sanitize_zip_name(req_item.name, max_len=45).replace(" ", "_") + clean_ext
                            folder_path = f"Brgy_{clean_b_name}/{section}/{record_folder}/{parent_folder}/{item_file_name}"
                        elif req_item:
                            item_file_name = sanitize_zip_name(req_item.name, max_len=45).replace(" ", "_") + clean_ext
                            folder_path = f"Brgy_{clean_b_name}/{section}/{record_folder}/{item_file_name}"
                        else:
                            clean_doc_fname = sanitize_file_name(raw_fname, max_name_len=40).replace(" ", "_")
                            folder_path = f"Brgy_{clean_b_name}/{section}/{record_folder}/Attachments/{clean_doc_fname}"

                        orig_path = folder_path
                        counter = 2
                        while folder_path in used_paths:
                            base_p, ext_p = os.path.splitext(orig_path)
                            folder_path = f"{base_p}_{counter}{ext_p}"
                            counter += 1
                        used_paths.add(folder_path)

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

    try:
        send_mail(
            subject='eTala Alert: Document Expiry Summary Notice',
            message=f'eTala Document Expiry Alert Summary: {expired_docs.count()} expired, {expiring_docs.count()} expiring soon.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        return True, f"Sent email notifications to {len(recipients)} staff/admin user(s) ({expired_docs.count()} expired, {expiring_docs.count()} expiring soon)."
    except Exception as e:
        err_str = str(e)
        logger.error(f"Failed to send expiry alerts email: {err_str}")
        if "resend.com/domains" in err_str or "only send testing emails" in err_str or "550" in err_str:
            return False, (
                "Resend SMTP Testing Mode: Emails can currently only be sent to your registered Resend test email (mardionjrcordetafuerte2@gmail.com). "
                "To deliver alerts to all municipality staff/admin emails, please verify your custom domain at resend.com/domains."
            )
        return False, f"Email delivery failed: {err_str}"



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
            
        headers = ['Log ID', 'Email Attempted', 'Status', 'Timestamp (PST)']
        def row_generator():
            yield headers
            for item in qs:
                yield [
                    item.id,
                    item.email_attempted,
                    "Success" if item.success else "Failed",
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
            
        headers = ['Log ID', 'User / Operator', 'Role', 'Action Executed', 'Target Record ID', 'Timestamp (PST)']
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
    else:
        # Only regularized (resolved) illegal constructions appear in Master Records.
        # Unresolved and pending_permit cases remain exclusively in the Illegal Constructions module.
        qs = qs.exclude(is_illegal_construction=True, illegal_compliance_status__in=['unresolved', 'pending_permit'])

    return qs
