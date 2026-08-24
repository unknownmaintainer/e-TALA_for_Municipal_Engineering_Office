import csv
import datetime
from datetime import timedelta
import io
import json
import logging
import os
import re
import zipfile

from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import EngineeringRecord, RecordRequirement, AuditLog, LoginAttempt, Document

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


# ─── UNIFIED EMAIL DISPATCH SERVICE (BREVO HTTP API + RESEND + SMTP FALLBACK) ───

def send_etala_email(subject, message, recipient_list, html_message=None, from_email=None, fail_silently=False):
    """
    Unified eTala email dispatcher:
    1. Brevo HTTP REST API v3 (Port 443 HTTPS — 100% bypasses cloud SMTP port blocks on Render/AWS/Heroku)
    2. Resend HTTP REST API (Port 443 HTTPS)
    3. Standard Django SMTP backend fallback
    """
    if not recipient_list:
        return False

    clean_recipients = [r.strip() for r in recipient_list if r and '@' in r]
    if not clean_recipients:
        return False

    raw_from = (from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'Municipal Engineering Office - Carigara <noreply@etala.gov.ph>')).strip()
    from email.utils import parseaddr, formataddr
    p_name, p_email = parseaddr(raw_from)
    sender_name = p_name or "Municipal Engineering Office - Carigara"
    sender_email = p_email or raw_from
    clean_from = formataddr((p_name, p_email)) if (p_name and p_email) else (p_email or raw_from)

    # Method 1: Brevo HTTP REST API v3
    brevo_key = os.getenv('BREVO_API_KEY', '').strip() or os.getenv('SENDINBLUE_API_KEY', '').strip()
    if not brevo_key:
        email_pass_raw = os.getenv('EMAIL_HOST_PASSWORD', '').strip()
        if email_pass_raw.startswith('xkeysib-'):
            brevo_key = email_pass_raw

    if brevo_key:
        try:
            import requests
            to_payload = [{"email": r} for r in clean_recipients]
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "accept": "application/json",
                    "api-key": brevo_key,
                    "content-type": "application/json",
                },
                json={
                    "sender": {
                        "name": sender_name,
                        "email": sender_email,
                    },
                    "to": to_payload,
                    "subject": subject,
                    "htmlContent": html_message or message,
                    "textContent": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"Email '{subject}' delivered via Brevo HTTP API to {clean_recipients}")
                return True
            else:
                logger.warning(f"Brevo HTTP API returned status {resp.status_code}: {resp.text}")
        except Exception as b_err:
            logger.warning(f"Brevo HTTP API dispatch error: {b_err}")

    # Method 2: Resend HTTP REST API
    resend_key = os.getenv('RESEND_API_KEY', '').strip()
    if resend_key:
        try:
            import requests
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": clean_from,
                    "to": clean_recipients,
                    "subject": subject,
                    "html": html_message or message,
                    "text": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"Email '{subject}' delivered via Resend HTTP API to {clean_recipients}")
                return True
            else:
                logger.warning(f"Resend HTTP API returned status {resp.status_code}: {resp.text}")
        except Exception as r_err:
            logger.warning(f"Resend HTTP API dispatch error: {r_err}")

    # Method 3: Standard Django SMTP Backend Fallback
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=clean_from,
            recipient_list=clean_recipients,
            html_message=html_message,
            fail_silently=fail_silently,
        )
        logger.info(f"Email '{subject}' delivered via standard SMTP backend to {clean_recipients}")
        return True
    except Exception as smtp_err:
        logger.error(f"Standard SMTP delivery failed for {clean_recipients}: {smtp_err}")
        if not fail_silently:
            raise smtp_err
        return False


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

def sanitize_zip_name(raw_name, max_len=80):
    """Sanitizes raw string and caps length cleanly at word boundaries for safe ZIP paths & filenames."""
    if not raw_name:
        return "item"
    cleaned = "".join(c for c in str(raw_name) if c.isalnum() or c in (' ', '_', '-')).strip()
    cleaned = re.sub(r'[\s_]+', '_', cleaned).strip('_')
    if len(cleaned) > max_len:
        # Avoid breaking words in half
        trimmed = cleaned[:max_len]
        if '_' in trimmed:
            last_us = trimmed.rfind('_')
            if last_us > 25:
                trimmed = trimmed[:last_us]
        cleaned = trimmed.strip('_')
    return cleaned or "item"


def sanitize_file_name(raw_filename, max_name_len=80):
    """Sanitizes filename and extension, preserving complete words."""
    if not raw_filename:
        return "document"
    name_part, ext_part = os.path.splitext(os.path.basename(str(raw_filename)))
    clean_name = sanitize_zip_name(name_part, max_len=max_name_len)
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
    # 1. ILLEGAL CONSTRUCTIONS & VIOLATIONS
    if record.is_illegal_construction:
        violator = ""
        if hasattr(record, 'permit_detail') and record.permit_detail and record.permit_detail.applicant_name:
            app = record.permit_detail.applicant_name.strip()
            if app.lower() not in ['n/a', 'none', '—', '', 'unknown', 'null', 'under investigation']:
                violator = sanitize_zip_name(app, max_len=50).replace(" ", "_")
        
        raw_title = (record.title or "").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=60).replace(" ", "_") if raw_title else ""
        
        if violator:
            base_slug = violator
        elif clean_title:
            base_slug = clean_title
        else:
            base_slug = "Violation_Case"

        if include_location:
            status_suffix = "Stop_Order"
            if record.illegal_compliance_status == 'resolved':
                status_suffix = "Regularized"
            elif record.illegal_compliance_status == 'pending_permit':
                status_suffix = "Permit_Filed"
            base_slug = f"{base_slug}_{status_suffix}"
            if record.barangay:
                b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=35).replace(" ", "_")
                base_slug = f"{base_slug}_Brgy_{b_name}"
        return base_slug

    # 2. STANDARD PERMITS
    elif record.record_type == 'Permit':
        applicant = ""
        if hasattr(record, 'permit_detail') and record.permit_detail:
            app = record.permit_detail.applicant_name.strip()
            if app.lower() not in ['n/a', 'none', '—', '', 'unknown', 'null']:
                applicant = sanitize_zip_name(app, max_len=50).replace(" ", "_")

        raw_title = (record.title or "").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=60).replace(" ", "_") if raw_title else ""

        if applicant:
            base_slug = applicant
        elif clean_title:
            base_slug = clean_title
        else:
            base_slug = "Permit_Record"

        if include_location:
            permit_type = record.specific_type_label or "Building_Permit"
            clean_type = sanitize_zip_name(permit_type, max_len=40).replace(" ", "_")
            if clean_type.lower() not in base_slug.lower():
                base_slug = f"{base_slug}_{clean_type}"
            if record.year and str(record.year) not in base_slug:
                base_slug = f"{base_slug}_{record.year}"
            if record.barangay:
                b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=35).replace(" ", "_")
                base_slug = f"{base_slug}_Brgy_{b_name}"
        return base_slug

    # 3. INFRASTRUCTURE PROJECTS
    else:
        raw_title = (record.title or "Infra_Project").strip()
        clean_title = sanitize_zip_name(raw_title, max_len=60).replace(" ", "_")
        base_slug = clean_title or "Infra_Project"

        if include_location:
            proj_type = record.specific_type_label or "Infra_Project"
            clean_proj_type = sanitize_zip_name(proj_type, max_len=40).replace(" ", "_")
            if clean_proj_type.lower() not in base_slug.lower():
                base_slug = f"{base_slug}_{clean_proj_type}"
            if record.year and str(record.year) not in base_slug:
                base_slug = f"{base_slug}_{record.year}"
            if record.barangay:
                b_name = sanitize_zip_name(record.barangay.barangay_name, max_len=35).replace(" ", "_")
                base_slug = f"{base_slug}_Brgy_{b_name}"
        return base_slug


def get_document_group_folder(doc, record):
    """
    Classifies an uploaded document into standardized, numbered lifecycle/document subfolders.
    Only creates folder paths for actual files (no empty folders).
    """
    req_name = (doc.requirement_item.name if doc.requirement_item else '').lower()
    parent_name = (doc.requirement_item.parent.name if doc.requirement_item and doc.requirement_item.parent else '').lower()
    doc_type = (doc.document_type or '').lower()
    file_name = (doc.file_name or (doc.file.name if doc.file else '')).lower()

    combined = f"{req_name} {parent_name} {doc_type} {file_name}"

    # 1. ILLEGAL CONSTRUCTIONS & VIOLATIONS
    if record.is_illegal_construction:
        if any(k in combined for k in ['inspection', 'spot', 'site inspection', 'gps', 'geotag', 'investigation', 'discovery']):
            return "01_Inspection"
        if any(k in combined for k in ['violation', 'stop order', 'stoppage', 'notice', 'demolition', 'cease', 'summons', 'citation']):
            return "02_Violation_and_Orders"
        if any(k in combined for k in ['compliance', 'response', 'hearing', 'minutes', 'explanation', 'undertaking', 'commitment']):
            return "03_Compliance"
        if any(k in combined for k in ['regularization', 'retroactive', 'penalty', 'official permit', 'as-built', 'approved permit']):
            return "04_Regularization"
        return "05_Supporting_Evidence"

    # 2. INFRASTRUCTURE PROJECTS (Municipal / Barangay Infra)
    elif record.record_type == 'Project':
        if any(k in combined for k in ['planning', 'feasibility', 'pow', 'program of work', 'program of works', 'detailed engineering', 'ded', 'concept', 'project brief']):
            return "01_Planning"
        if any(k in combined for k in ['procurement', 'bid', 'bidding', 'philgeps', 'bac', 'abstract', 'eligibility', 'invitation to bid', 'itb', 'post-qualification']):
            return "02_Procurement"
        if any(k in combined for k in ['contract', 'award', 'noa', 'notice of award', 'ntp', 'notice to proceed', 'performance bond', 'agreement']):
            return "03_Contract_and_Award"
        if any(k in combined for k in ['construction', 'progress', 'billing', 'statement of work', 's-curve', 'site photo', 'picture', 'variation', 'change order', 'time extension', 'inspection report']):
            return "04_Construction"
        if any(k in combined for k in ['completion', 'turnover', 'turn-over', 'acceptance', 'warranty', 'certificate of completion', 'final inspection', 'final billing', 'completion report', 'acceptance report']):
            return "05_Completion"
        return "06_Other_Supporting_Documents"

    # 3. PERMITS (Building, Electrical, Plumbing, Fencing, Demolition, Occupancy, etc.)
    else:
        if any(k in combined for k in ['application', 'form', 'unified', 'dti', 'sec', 'affidavit', 'ownership', 'title', 'tax dec', 'deed', 'lease', 'contract of lease', 'lot', 'land']):
            return "01_Application"
        if any(k in combined for k in ['plan', 'blueprint', 'architectural', 'structural plan', 'electrical plan', 'plumbing plan', 'sanitary plan', 'mechanical plan', 'electronics plan', 'specifications', 'bill of materials', 'bom', 'cost estimate', 'specs']):
            return "02_Plans_and_Specifications"
        if any(k in combined for k in ['clearance', 'certificate', 'fsec', 'fsic', 'fire', 'zoning', 'barangay clearance', 'locational', 'environmental', 'ecc', 'dpwh', 'caap', 'resolution']):
            return "03_Clearances_and_Certifications"
        if any(k in combined for k in ['technical', 'structural analysis', 'geotechnical', 'soil', 'seismic', 'calculation', 'design computation', 'boring', 'load test']):
            return "04_Technical_Documents"
        if any(k in combined for k in ['receipt', 'official receipt', 'payment', 'assessment', 'tax receipt', 'order of payment', 'fee', 'or']):
            return "05_Payments_and_Receipts"
        return "06_Other_Supporting_Documents"


def generate_record_summary_text(record, user=None):
    """
    Generates a clean, human-readable, jargon-free 00_RECORD_SUMMARY.txt content for an EngineeringRecord.
    """
    now = timezone.now()
    now_str = now.strftime('%B %d, %Y by ') + (user.get_full_name() or user.username if user and hasattr(user, 'username') else 'Administrator')
    if user and hasattr(user, 'role') and user.role:
        now_str += f" ({user.role.title()})"

    encoded_by_name = "Office Staff"
    if record.created_by:
        encoded_by_name = record.created_by.get_full_name() or record.created_by.username
        if hasattr(record.created_by, 'role') and record.created_by.role:
            encoded_by_name += f" ({record.created_by.role.title()})"
    encoded_date_str = record.created_at.strftime('%B %d, %Y') + f" by {encoded_by_name}" if record.created_at else f"by {encoded_by_name}"

    record_title = record.title
    if record.record_type == 'Permit' and hasattr(record, 'permit_detail') and record.permit_detail and record.permit_detail.applicant_name:
        applicant = record.permit_detail.applicant_name
        record_title = f"{applicant} ({record.title or 'Building Permit'})"

    type_str = f"{record.record_type}"
    if record.record_type == 'Project' and record.project_scope:
        type_str = f"{record.project_scope} Project"
    elif record.record_type == 'Permit' and hasattr(record, 'permit_detail') and record.permit_detail and record.permit_detail.permit_type:
        type_str = f"{record.permit_detail.permit_type} Permit"
    elif record.is_illegal_construction:
        type_str = "Illegal Construction"

    barangay_name = record.barangay.barangay_name if record.barangay else "Carigara, Leyte"
    type_and_brgy = f"{type_str} • {barangay_name}"

    cost_str = None
    if record.record_type == 'Project' and hasattr(record, 'project_detail') and record.project_detail and record.project_detail.project_cost:
        cost_str = f"PHP {record.project_detail.project_cost:,.2f}"
    elif hasattr(record, 'permit_detail') and record.permit_detail and getattr(record.permit_detail, 'estimated_cost', None):
        cost_str = f"PHP {record.permit_detail.estimated_cost:,.2f}"

    # Calculate upload stats
    leaf_reqs = record.requirements.filter(
        requirement_item__is_group=False,
        requirement_item__sub_items__isnull=True
    ).select_related('requirement_item', 'requirement_item__parent', 'document').order_by('requirement_item__order', 'req_id')

    total_leaf = leaf_reqs.count()
    fulfilled_count = leaf_reqs.filter(is_fulfilled=True, document__isnull=False).count()
    waived_count = leaf_reqs.filter(is_waived=True).count()
    pending_count = total_leaf - fulfilled_count - waived_count
    if pending_count < 0:
        pending_count = 0

    if total_leaf > 0:
        if pending_count == 0:
            upload_status = f"{fulfilled_count} of {total_leaf} Uploaded • 100% Completed"
        else:
            upload_status = f"{fulfilled_count} of {total_leaf} Uploaded • {pending_count} Pending"
    else:
        upload_status = f"{record.documents.count()} Files Uploaded"

    lines = [
        "=" * 80,
        "                    OFFICE OF THE MUNICIPAL ENGINEER",
        "                       Carigara, Leyte • eTala System",
        "=" * 80,
        "",
        "RECORD SUMMARY",
        "-" * 80,
        f"Project / Record : {record_title}",
        f"Type & Barangay  : {type_and_brgy}",
    ]
    if cost_str:
        lines.append(f"Project Budget   : {cost_str}")
    lines.extend([
        f"Encoded Date     : {encoded_date_str}",
        f"Downloaded Date  : {now_str}",
        f"Upload Status    : {upload_status}",
        "",
        "=" * 80,
        "LIST OF FILES & DOCUMENTS",
        "=" * 80,
        "",
    ])

    # Grouped Requirements vs Standalone
    parent_groups = {}
    standalone_items = []

    for req in leaf_reqs:
        parent = req.requirement_item.parent
        if parent:
            if parent.item_id not in parent_groups:
                parent_groups[parent.item_id] = {
                    'name': parent.name,
                    'sequence': parent.order or 99,
                    'items': []
                }
            parent_groups[parent.item_id]['items'].append(req)
        else:
            standalone_items.append(req)

    sorted_groups = sorted(parent_groups.values(), key=lambda g: g['sequence'])
    group_idx = 1

    for group in sorted_groups:
        clean_gname = re.sub(r'^\d+[\s_.-]*', '', group['name']).replace(' ', '_')
        folder_label = f"0{group_idx}_{clean_gname}" if group_idx < 10 else f"{group_idx}_{clean_gname}"
        lines.append(f"📁 {folder_label}/")
        for idx, item in enumerate(group['items']):
            is_last = (idx == len(group['items']) - 1)
            prefix = "   └── " if is_last else "   ├── "
            if item.is_fulfilled and item.document:
                fname = item.document.file_name or (os.path.basename(item.document.file.name) if item.document.file else f"{item.requirement_item.name}.pdf")
                lines.append(f"{prefix}[UPLOADED] {fname}")
            elif item.is_waived:
                lines.append(f"{prefix}[N/A]      {item.requirement_item.name} (Waived / Not Required)")
            else:
                lines.append(f"{prefix}[PENDING]  {item.requirement_item.name} (No file yet)")
        lines.append("")
        group_idx += 1

    # Standalone items
    if standalone_items:
        lines.append("📄 OTHER DOCUMENTS")
        for idx, item in enumerate(standalone_items):
            is_last = (idx == len(standalone_items) - 1)
            prefix = "   └── " if is_last else "   ├── "
            if item.is_fulfilled and item.document:
                fname = item.document.file_name or (os.path.basename(item.document.file.name) if item.document.file else f"{item.requirement_item.name}.pdf")
                lines.append(f"{prefix}[UPLOADED] {fname}")
            elif item.is_waived:
                lines.append(f"{prefix}[N/A]      {item.requirement_item.name} (Waived / Not Required)")
            else:
                lines.append(f"{prefix}[PENDING]  {item.requirement_item.name} (No file yet)")
        lines.append("")

    # Additional attachments
    extra_docs = record.documents.filter(requirement_item__isnull=True)
    if extra_docs.exists():
        att_folder = f"0{group_idx}_Additional_Attachments" if group_idx < 10 else f"{group_idx}_Additional_Attachments"
        lines.append(f"📁 {att_folder}/")
        for idx, edoc in enumerate(extra_docs):
            is_last = (idx == extra_docs.count() - 1)
            prefix = "   └── " if is_last else "   ├── "
            fname = edoc.file_name or (os.path.basename(edoc.file.name) if edoc.file else 'attachment')
            lines.append(f"{prefix}{fname}")
        lines.append("")

    lines.extend([
        "=" * 80,
        "Generated by eTala for Carigara Engineering Office Records.",
        "=" * 80,
        ""
    ])

    return "\n".join(lines)


def generate_barangay_summary_text(barangay, records, user=None):
    """
    Generates a clean, human-readable 00_BARANGAY_SUMMARY.txt content for an entire Barangay archive.
    """
    now = timezone.now()
    now_str = now.strftime('%B %d, %Y by ') + (user.get_full_name() or user.username if user and hasattr(user, 'username') else 'Administrator')
    if user and hasattr(user, 'role') and user.role:
        now_str += f" ({user.role.title()})"

    total_records = records.count()
    permits_count = records.filter(record_type='Permit').count()
    muni_projects = records.filter(record_type='Project', project_scope='Municipal').count()
    brgy_projects = records.filter(record_type='Project', project_scope='Barangay').count()
    illegal_cases = records.filter(is_illegal_construction=True).count()

    lines = [
        "=" * 80,
        "                    OFFICE OF THE MUNICIPAL ENGINEER",
        "                       Carigara, Leyte • eTala System",
        "=" * 80,
        "",
        "BARANGAY ARCHIVE SUMMARY",
        "-" * 80,
        f"Barangay Name    : {barangay.barangay_name}, Carigara, Leyte",
        f"Downloaded Date  : {now_str}",
        f"Total Records    : {total_records} Records (Municipal: {muni_projects} • Barangay: {brgy_projects} • Permits: {permits_count} • Violations: {illegal_cases})",
        "",
        "=" * 80,
        "ARCHIVE FOLDER STRUCTURE",
        "=" * 80,
        "",
        "📁 01_Municipal_Projects/",
    ]

    for rec in records.filter(record_type='Project', project_scope='Municipal'):
        lines.append(f"   └── 📁 {get_record_export_name(rec, include_location=False)}/")

    lines.append("")
    lines.append("📁 02_Barangay_Projects/")
    for rec in records.filter(record_type='Project', project_scope='Barangay'):
        lines.append(f"   └── 📁 {get_record_export_name(rec, include_location=False)}/")

    lines.append("")
    lines.append("📁 03_Building_Permits/")
    for rec in records.filter(record_type='Permit'):
        lines.append(f"   └── 📁 {get_record_export_name(rec, include_location=False)}/")

    if illegal_cases > 0:
        lines.append("")
        lines.append("📁 04_Illegal_Constructions/")
        for rec in records.filter(is_illegal_construction=True):
            lines.append(f"   └── 📁 {get_record_export_name(rec, include_location=False)}/")

    lines.extend([
        "",
        "=" * 80,
        "Generated by eTala for Carigara Engineering Office Records.",
        "=" * 80,
        ""
    ])

    return "\n".join(lines)


def build_record_zip_buffer(record, stream_getter_func, user=None):
    """
    Generates an in-memory ZIP archive buffer containing all fulfilled documents for an EngineeringRecord.
    Structure:
      ├── 00_RECORD_SUMMARY.txt
      ├── 01_Building_Plans/ (Sub-folders only for multi-item parent groups)
      │   └── Plan_and_Profiles.pdf
      ├── 03_Specifications.pdf (Direct loose file for standalone requirements)
      └── 06_Additional_Attachments/ (Photos / miscellaneous)
    """
    buffer = io.BytesIO()
    used_paths = set()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add 00_RECORD_SUMMARY.txt at root of ZIP
        summary_text = generate_record_summary_text(record, user=user)
        zip_file.writestr("00_RECORD_SUMMARY.txt", summary_text.encode('utf-8'))
        used_paths.add("00_RECORD_SUMMARY.txt")

        # Map parent group requirement items to sequence numbers
        leaf_reqs = record.requirements.filter(
            requirement_item__is_group=False,
            requirement_item__sub_items__isnull=True
        ).select_related('requirement_item', 'requirement_item__parent', 'document')

        parent_groups = {}
        for req in leaf_reqs:
            parent = req.requirement_item.parent
            if parent and parent.item_id not in parent_groups:
                parent_groups[parent.item_id] = {
                    'name': parent.name,
                    'sequence': parent.order or 99
                }
        sorted_groups = sorted(parent_groups.items(), key=lambda x: x[1]['sequence'])
        group_folder_map = {}
        for g_idx, (p_id, p_info) in enumerate(sorted_groups, start=1):
            clean_gname = re.sub(r'^\d+[\s_.-]*', '', p_info['name']).replace(' ', '_')
            group_folder_map[p_id] = f"0{g_idx}_{clean_gname}" if g_idx < 10 else f"{g_idx}_{clean_gname}"

        # 2. Add all documents
        for doc in record.documents.select_related('requirement_item', 'requirement_item__parent'):
            try:
                file_obj, _, url = stream_getter_func(doc)
                if not file_obj and url:
                    try:
                        import requests
                        r = requests.get(url, timeout=15)
                        if r.status_code == 200:
                            file_obj = io.BytesIO(r.content)
                    except Exception:
                        pass
                if file_obj:
                    file_data = file_obj.read()
                    if hasattr(file_obj, 'close'):
                        file_obj.close()

                    raw_fname = doc.file_name or (doc.file.name if doc.file else 'document')
                    _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                    clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'

                    req_item = doc.requirement_item
                    if req_item:
                        clean_item_name = re.sub(r'\s*\([a-z]\.\d+\)', '', req_item.name).strip()
                        clean_item_name = re.sub(r'^\d+[\s_.-]*', '', clean_item_name).strip()
                        item_file_name = sanitize_zip_name(clean_item_name, max_len=80).replace(" ", "_") + clean_ext

                        if req_item.parent_id and req_item.parent_id in group_folder_map:
                            folder_prefix = group_folder_map[req_item.parent_id]
                            file_path = f"{folder_prefix}/{item_file_name}"
                        else:
                            file_path = item_file_name
                    else:
                        clean_extra = sanitize_file_name(raw_fname, max_name_len=80).replace(" ", "_")
                        file_path = f"Additional_Attachments/{clean_extra}"

                    # Prevent duplicate zip path collisions & handle versioning
                    orig_path = file_path
                    counter = 2
                    while file_path in used_paths:
                        base_p, ext_p = os.path.splitext(orig_path)
                        file_path = f"{base_p}_v{counter}_REPLACED{ext_p}"
                        counter += 1
                    used_paths.add(file_path)

                    zip_file.writestr(file_path, file_data)
            except Exception as exc:
                logger.error(f"Error zipping record document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_category_zip_buffer(record, parent_req, stream_getter_func):
    """
    Generates an in-memory ZIP archive buffer containing all documents under a specific requirement parent category.
    """
    parent_item = parent_req.requirement_item
    sub_items = list(parent_item.sub_items.all())

    sub_reqs = RecordRequirement.objects.filter(
        record=record, requirement_item__in=sub_items
    ).select_related('requirement_item', 'document')

    buffer = io.BytesIO()
    used_paths = set()
    processed_doc_ids = set()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for req in sub_reqs:
            if req.document and req.document.document_id not in processed_doc_ids:
                try:
                    file_obj, _, url = stream_getter_func(req.document)
                    if not file_obj and url:
                        try:
                            import requests
                            r = requests.get(url, timeout=15)
                            if r.status_code == 200:
                                file_obj = io.BytesIO(r.content)
                        except Exception:
                            pass
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()

                        raw_fname = req.document.file_name or (req.document.file.name if req.document.file else 'document')
                        _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                        clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'
                        clean_item_name = re.sub(r'\s*\([a-z]\.\d+\)', '', req.requirement_item.name).strip()
                        item_file_name = sanitize_zip_name(clean_item_name, max_len=80).replace(" ", "_") + clean_ext
                        file_path = item_file_name

                        orig_path = file_path
                        counter = 2
                        while file_path in used_paths:
                            base_p, ext_p = os.path.splitext(orig_path)
                            file_path = f"{base_p}_v{counter}_REPLACED{ext_p}"
                            counter += 1
                        used_paths.add(file_path)
                        processed_doc_ids.add(req.document.document_id)

                        zip_file.writestr(file_path, file_data)
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
                    file_path = clean_doc_fname

                    orig_path = file_path
                    counter = 2
                    while file_path in used_paths:
                        base_p, ext_p = os.path.splitext(orig_path)
                        file_path = f"{base_p}_v{counter}_REPLACED{ext_p}"
                        counter += 1
                    used_paths.add(file_path)
                    processed_doc_ids.add(doc.document_id)

                    zip_file.writestr(file_path, file_data)
            except Exception as exc:
                logger.error(f"Error zipping direct document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_barangay_zip_buffer(barangay, stream_getter_func, user=None):
    """
    Generates an in-memory ZIP archive buffer containing all documents for an entire Barangay.
    Clean structure:
      Barangay_Balilit/
        ├── 00_BARANGAY_SUMMARY.txt
        ├── 01_Municipal_Projects/
        │   └── Water_System_Project/
        │       ├── 00_RECORD_SUMMARY.txt
        │       ├── 01_Building_Plans/
        │       └── 03_Specifications.pdf
        ├── 02_Barangay_Projects/
        ├── 03_Building_Permits/
        └── 04_Illegal_Constructions/
    """
    buffer = io.BytesIO()
    clean_b_name = sanitize_zip_name(barangay.barangay_name, max_len=30).replace(" ", "_")
    records = EngineeringRecord.objects.filter(barangay=barangay).exclude(status='archived').prefetch_related(
        'documents__requirement_item__parent'
    )

    used_record_folders = {}
    assigned_folders = set()
    used_paths = set()

    for record in records:
        base_name = get_record_export_name(record, include_location=False)
        section = (
            "04_Illegal_Constructions" if record.is_illegal_construction else
            ("03_Building_Permits" if record.record_type == 'Permit' else
             ("01_Municipal_Projects" if record.project_scope == 'Municipal' else "02_Barangay_Projects"))
        )
        unique_key = f"{section}/{base_name}"
        if unique_key in assigned_folders:
            suffix_label = f"Case-{record.record_id}" if record.is_illegal_construction else f"Rec-{record.record_id}"
            base_name = f"{base_name}_{suffix_label}"
            unique_key = f"{section}/{base_name}"
            counter = 2
            while unique_key in assigned_folders:
                base_name = f"{base_name}_{counter}"
                unique_key = f"{section}/{base_name}"
                counter += 1
        assigned_folders.add(unique_key)
        used_record_folders[record.record_id] = (section, base_name)

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add Master 00_BARANGAY_SUMMARY.txt
        brgy_summary = generate_barangay_summary_text(barangay, records, user=user)
        zip_file.writestr(f"{clean_b_name}/00_BARANGAY_SUMMARY.txt", brgy_summary.encode('utf-8'))
        used_paths.add(f"{clean_b_name}/00_BARANGAY_SUMMARY.txt")

        # 2. Add each record and its documents
        for record in records:
            section, record_folder = used_record_folders.get(
                record.record_id,
                ("01_Municipal_Projects", get_record_export_name(record, include_location=False))
            )
            rec_prefix = f"{clean_b_name}/{section}/{record_folder}"

            # Add record's own summary file
            rec_summary = generate_record_summary_text(record, user=user)
            rec_summary_path = f"{rec_prefix}/00_RECORD_SUMMARY.txt"
            if rec_summary_path not in used_paths:
                zip_file.writestr(rec_summary_path, rec_summary.encode('utf-8'))
                used_paths.add(rec_summary_path)

            # Map parent groups
            leaf_reqs = record.requirements.filter(
                requirement_item__is_group=False,
                requirement_item__sub_items__isnull=True
            ).select_related('requirement_item', 'requirement_item__parent')

            parent_groups = {}
            for req in leaf_reqs:
                parent = req.requirement_item.parent
                if parent and parent.item_id not in parent_groups:
                    parent_groups[parent.item_id] = {
                        'name': parent.name,
                        'sequence': parent.order or 99
                    }
            sorted_groups = sorted(parent_groups.items(), key=lambda x: x[1]['sequence'])
            group_folder_map = {}
            for g_idx, (p_id, p_info) in enumerate(sorted_groups, start=1):
                clean_gname = re.sub(r'^\d+[\s_.-]*', '', p_info['name']).replace(' ', '_')
                group_folder_map[p_id] = f"0{g_idx}_{clean_gname}" if g_idx < 10 else f"{g_idx}_{clean_gname}"

            for doc in record.documents.all():
                try:
                    file_obj, _, url = stream_getter_func(doc)
                    if not file_obj and url:
                        try:
                            import requests
                            r = requests.get(url, timeout=15)
                            if r.status_code == 200:
                                file_obj = io.BytesIO(r.content)
                        except Exception:
                            pass
                    if file_obj:
                        file_data = file_obj.read()
                        if hasattr(file_obj, 'close'):
                            file_obj.close()

                        raw_fname = doc.file_name or (doc.file.name if doc.file else 'document')
                        _, ext_part = os.path.splitext(os.path.basename(str(raw_fname)))
                        clean_ext = "".join(c for c in ext_part if c.isalnum() or c == '.').strip() or '.pdf'

                        req_item = doc.requirement_item
                        if req_item:
                            clean_item_name = re.sub(r'\s*\([a-z]\.\d+\)', '', req_item.name).strip()
                            clean_item_name = re.sub(r'^\d+[\s_.-]*', '', clean_item_name).strip()
                            item_file_name = sanitize_zip_name(clean_item_name, max_len=60).replace(" ", "_") + clean_ext

                            if req_item.parent_id and req_item.parent_id in group_folder_map:
                                folder_prefix = group_folder_map[req_item.parent_id]
                                folder_path = f"{rec_prefix}/{folder_prefix}/{item_file_name}"
                            else:
                                folder_path = f"{rec_prefix}/{item_file_name}"
                        else:
                            clean_extra = sanitize_file_name(raw_fname, max_name_len=50).replace(" ", "_")
                            folder_path = f"{rec_prefix}/Additional_Attachments/{clean_extra}"

                        orig_path = folder_path
                        counter = 2
                        while folder_path in used_paths:
                            base_p, ext_p = os.path.splitext(orig_path)
                            folder_path = f"{base_p}_v{counter}_REPLACED{ext_p}"
                            counter += 1
                        used_paths.add(folder_path)

                        zip_file.writestr(folder_path, file_data)
                except Exception as exc:
                    logger.error(f"Error zipping barangay document {doc.document_id}: {exc}")

    buffer.seek(0)
    return buffer


def build_municipal_zip_buffer(stream_getter_func, user=None):
    """
    Generates an in-memory ZIP archive buffer containing all documents for the entire Municipality.
    """
    buffer = io.BytesIO()
    barangays = Barangay.objects.all().order_by('barangay_name')
    today_str = timezone.now().strftime('%Y-%m-%d')
    used_paths = set()

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        summary_lines = [
            "=" * 80,
            "                    OFFICE OF THE MUNICIPAL ENGINEER",
            "                       Carigara, Leyte • eTala System",
            "=" * 80,
            "",
            "FULL MUNICIPAL ARCHIVE SUMMARY",
            "-" * 80,
            f"Exported Date    : {timezone.now().strftime('%B %d, %Y')}",
            f"Total Barangays  : {barangays.count()} Barangays",
            f"Total Records    : {EngineeringRecord.objects.exclude(status='archived').count()} Records",
            "",
            "=" * 80,
            "BARANGAYS INCLUDED IN THIS ARCHIVE",
            "=" * 80,
        ]
        for b in barangays:
            summary_lines.append(f"📁 {sanitize_zip_name(b.barangay_name).replace(' ', '_')}/")
        summary_lines.extend(["", "=" * 80, "Generated by eTala for Carigara Engineering Office Records.", "=" * 80, ""])

        zip_file.writestr(f"Carigara_Engineering_Records_{today_str}/00_MUNICIPAL_SUMMARY.txt", "\n".join(summary_lines).encode('utf-8'))

        for b in barangays:
            b_buf = build_barangay_zip_buffer(b, stream_getter_func, user=user)
            with zipfile.ZipFile(b_buf, 'r') as b_zip:
                for item_name in b_zip.namelist():
                    b_data = b_zip.read(item_name)
                    dest_path = f"Carigara_Engineering_Records_{today_str}/{item_name}"
                    if dest_path not in used_paths:
                        zip_file.writestr(dest_path, b_data)
                        used_paths.add(dest_path)

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
    thirty_days_ago = today_date - timedelta(days=30)
    
    from .models import Document
    alert_docs = Document.objects.filter(
        expiry_date__isnull=False
    ).exclude(engineering_record__status='archived').select_related('engineering_record', 'requirement_item')
    
    expired_docs = alert_docs.filter(expiry_date__range=(thirty_days_ago, today_date)).order_by('-expiry_date')
    expiring_docs = alert_docs.filter(expiry_date__range=(today_date, thirty_days_later)).order_by('expiry_date')
    
    if not expired_docs.exists() and not expiring_docs.exists():
        return False, "No expired or expiring documents found."
        
    User = get_user_model()
    recipients = list(User.objects.filter(is_active=True, role__in=['admin', 'staff']).values_list('email', flat=True))
    if not recipients:
        return False, "No active admin/staff email recipients found."

    expired_items = "".join([f"<li><strong>{d.requirement_item.name if d.requirement_item else d.document_type}</strong> — {d.engineering_record.title} (Expired last {d.expiry_date.strftime('%b %d, %Y')})</li>" for d in expired_docs[:10]])
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
        success = send_etala_email(
            subject='eTala Alert: Document Expiry Summary Notice',
            message=f'eTala Document Expiry Alert Summary: {expired_docs.count()} expired, {expiring_docs.count()} expiring soon.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        if success:
            return True, f"Sent email notifications to {len(recipients)} staff/admin user(s) ({expired_docs.count()} expired, {expiring_docs.count()} expiring soon)."
        else:
            return False, "Failed to deliver email notifications."
    except Exception as e:
        err_str = str(e)
        logger.error(f"Failed to send expiry alerts email: {err_str}")
        if "resend.com/domains" in err_str or "only send testing emails" in err_str:
            return False, (
                "Email Sandbox Mode: To deliver alerts to all municipality staff/admin emails, please ensure your Brevo/SMTP sender email is verified."
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
        if date_filter in ['today', '24h']:
            qs = qs.filter(timestamp__date=now.date())
        elif date_filter in ['7days', '7d']:
            qs = qs.filter(timestamp__gte=now - timedelta(days=7))
        elif date_filter in ['30days', '30d']:
            qs = qs.filter(timestamp__gte=now - timedelta(days=30))
            
        if action_type == 'success':
            qs = qs.filter(success=True)
        elif action_type == 'failed':
            qs = qs.filter(success=False)
            
        if query:
            qs = qs.filter(email_attempted__icontains=query)
            
        headers = ['#', 'Date & Time (PST)', 'Account / Email', 'Login Status']
        def row_generator():
            yield headers
            for idx, item in enumerate(qs, start=1):
                yield [
                    idx,
                    item.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    item.email_attempted or "Unknown",
                    "SUCCESSFUL" if item.success else "FAILED"
                ]
        return f"eTala_Login_Attempts_{now.strftime('%Y%m%d_%H%M')}.csv", row_generator()
    else:
        qs = AuditLog.objects.all().select_related('user').exclude(
            Q(action__iexact='Logged out') |
            Q(action__iexact='Failed login attempt') |
            Q(action__icontains='Exported') |
            Q(action__icontains='profile picture') |
            Q(action__startswith='NOTIF_') |
            Q(action__startswith='Downloaded ') |
            Q(action__startswith='Requirement ')
        ).order_by('-performed_at')
        if current_user.role != 'admin':
            qs = qs.filter(user=current_user)
            
        if date_filter in ['today', '24h']:
            qs = qs.filter(performed_at__date=now.date())
        elif date_filter in ['7days', '7d']:
            qs = qs.filter(performed_at__gte=now - timedelta(days=7))
        elif date_filter in ['30days', '30d']:
            qs = qs.filter(performed_at__gte=now - timedelta(days=30))
            
        if action_type and action_type != 'all':
            qs = qs.filter(action__icontains=action_type)
            
        if query:
            qs = qs.filter(Q(action__icontains=query) | Q(user__username__icontains=query) | Q(user__full_name__icontains=query))
            
        headers = ['#', 'Date & Time (PST)', 'Staff / Operator', 'Role', 'Action Executed', 'Target Record ID']
        def row_generator():
            yield headers
            for idx, item in enumerate(qs, start=1):
                if item.user:
                    user_str = item.user.full_name or item.user.username
                    role_str = item.user.get_role_display()
                else:
                    user_str = "System"
                    role_str = "System"
                yield [
                    idx,
                    item.performed_at.strftime("%Y-%m-%d %H:%M:%S"),
                    user_str,
                    role_str,
                    item.action,
                    item.target_record_id or "—"
                ]
        return f"eTala_Audit_Trail_{now.strftime('%Y%m%d_%H%M')}.csv", row_generator()


# ─── REUSABLE RECORD FILTER SERVICE ──────────────────────────────────────────

def filter_engineering_records(base_qs, query='', record_type='', project_scope='', barangay_id='', status='', year='', permit_type='', project_type='', illegal_filter=''):
    """
    Applies high-precision search and filter criteria to an EngineeringRecord QuerySet.
    """
    qs = base_qs
    if query:
        q_clean = str(query).strip()
        tokens = [t for t in q_clean.split() if t]
        
        # Build composite multi-term AND query for maximum search accuracy
        for token in tokens:
            token_lower = token.lower()
            token_filter = (
                Q(title__icontains=token) |
                Q(barangay__barangay_name__icontains=token) |
                Q(permit_detail__permit_number__icontains=token) |
                Q(permit_detail__applicant_name__icontains=token) |
                Q(project_detail__contractor__icontains=token) |
                Q(permit_detail__permit_type__icontains=token) |
                Q(project_detail__project_type__icontains=token)
            )
            
            # High-Accuracy Status Keyword Matching (Matches true database status)
            if token_lower == 'issued':
                token_filter |= Q(record_type='Permit', status__in=['active', 'completed']).exclude(is_illegal_construction=True, illegal_compliance_status='resolved')
            elif token_lower in ['pending', 'unissued']:
                token_filter |= Q(status='pending')
            elif token_lower in ['ongoing', 'progress']:
                token_filter |= Q(record_type='Project', status__in=['active', 'in_progress'])
            elif token_lower == 'completed':
                token_filter |= Q(record_type='Project', status='completed')
            elif token_lower == 'regularized':
                token_filter |= Q(is_illegal_construction=True, illegal_compliance_status='resolved')
            elif token_lower == 'unresolved':
                token_filter |= Q(is_illegal_construction=True, illegal_compliance_status='unresolved')
            
            # Numeric token matching for Record IDs
            num_clean = re.sub(r'^[#recREC\-\s]+', '', token)
            if num_clean.isdigit():
                num_val = int(num_clean)
                token_filter |= Q(record_id=num_val)
            
            qs = qs.filter(token_filter)

        qs = qs.distinct()

    if record_type and record_type != 'Illegal':
        qs = qs.filter(record_type=record_type)
    if project_scope:
        qs = qs.filter(project_scope=project_scope)
    if barangay_id:
        qs = qs.filter(barangay_id=barangay_id)
    if status:
        if status in ['ongoing', 'in_progress']:
            qs = qs.filter(record_type='Project', status__in=['active', 'in_progress', 'pending'])
        elif status == 'completed':
            qs = qs.filter(record_type='Project', status='completed')
        elif status == 'issued':
            qs = qs.filter(record_type='Permit').exclude(is_illegal_construction=True, illegal_compliance_status='resolved').filter(status__in=['active', 'completed'])
        elif status == 'pending':
            qs = qs.filter(status='pending')
        elif status == 'regularized':
            qs = qs.filter(is_illegal_construction=True, illegal_compliance_status='resolved')
        elif status == 'active':
            qs = qs.filter(
                Q(record_type='Permit', status__in=['active', 'completed']) |
                Q(record_type='Project', status__in=['active', 'in_progress'])
            )
        else:
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


# ─── DEVICE AUTHORIZATION & SECURITY NOTIFICATION SERVICES ───────────────────

import secrets
import threading
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import send_mail


def parse_device_user_agent(ua_string):
    """Parses raw user agent string into friendly Device Name (OS + Browser)."""
    if not ua_string:
        return "Windows PC • Browser"

    ua = ua_string.lower()

    # Detect OS
    os_name = "Desktop PC"
    if "windows nt 10.0" in ua or "windows nt 11.0" in ua or "windows nt" in ua:
        os_name = "Windows PC"
    elif "macintosh" in ua or "mac os x" in ua:
        os_name = "Apple Mac"
    elif "iphone" in ua:
        os_name = "iPhone"
    elif "ipad" in ua:
        os_name = "iPad"
    elif "android" in ua:
        os_name = "Android Mobile"
    elif "linux" in ua:
        os_name = "Linux PC"

    # Detect Browser
    browser_name = "Browser"
    if "edg/" in ua or "edge" in ua:
        browser_name = "Microsoft Edge"
    elif "chrome/" in ua or "crios/" in ua:
        browser_name = "Google Chrome"
    elif "firefox/" in ua:
        browser_name = "Mozilla Firefox"
    elif "safari/" in ua and "chrome/" not in ua:
        browser_name = "Apple Safari"
    elif "opera/" in ua or "opr/" in ua:
        browser_name = "Opera"

    return f"{os_name} • {browser_name}"


def get_client_device_token(request):
    """Retrieves existing device token from cookie or creates a unique 48-char random hex token."""
    token = request.COOKIES.get('etala_device_token', '').strip()
    if not token or len(token) < 16:
        token = secrets.token_hex(24)
    return token


def dispatch_device_approval_request(user, device, request):
    """Legacy stub - device approval is now handled via self-service 2FA Email OTP."""
    pass


def dispatch_new_device_login_alert(user, device, request):
    """Sends immediate security alert email to user's registered Gmail when logging in from a new device."""
    if not user.email or '@' not in user.email:
        return

    user_full_name = user.full_name or user.get_full_name() or user.username
    subject = f'🛡️ eTala Security Notice — New Device Login Detected'
    timestamp_str = timezone.now().strftime('%b %d, %Y • %I:%M %p')

    html_content = render_to_string('emails/email_new_device_alert.html', {
        'user_full_name': user_full_name,
        'device_name': device.device_name,
        'timestamp': timestamp_str,
    })

    plain_content = (
        f"Hello {user_display},\n\n"
        f"Your eTala account was recently logged into from a new device: {device.device_name} (IP: {device.ip_address}) on {timestamp_str}.\n"
        f"If this was you, no action is needed.\n"
        f"If you did not log in, please contact the Municipal Engineering Office Administrator immediately.\n"
    )

    def _send_user_alert():
        try:
            send_etala_email(
                subject=subject,
                message=plain_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"New device alert sent to user email: {user.email}")
        except Exception as exc:
            logger.warning(f"Failed sending new device alert to {user.email}: {exc}")

    threading.Thread(target=_send_user_alert, daemon=True).start()

