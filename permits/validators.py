from django.core.exceptions import ValidationError
from django.utils.html import escape
import os
import re

def virus_scan_file(file):
    """
    Mock virus scan hook.
    In a real production environment, this calls ClamAV or an API-based scanner.
    If the filename contains 'eicar' (standard virus test file name), simulate virus detection.
    """
    if 'eicar' in file.name.lower():
        raise ValidationError("Security Violation: Potential malware detected during automated virus scan.")
    return True

MINIMUM_BACKLOG_YEAR = 1995

def validate_backlog_year(year_or_date):
    """
    Validates that an engineering record or permit year/date is not prior to 1995.
    eTala archival policy specifies that 1995 is the minimum acceptable backlog year.
    """
    if not year_or_date:
        return True
    import datetime
    if isinstance(year_or_date, (datetime.date, datetime.datetime)):
        yr = year_or_date.year
    else:
        try:
            yr = int(str(year_or_date).strip()[:4])
        except (ValueError, TypeError):
            return True
    if yr < MINIMUM_BACKLOG_YEAR:
        raise ValidationError(
            f"Invalid Year ({yr}): Records prior to {MINIMUM_BACKLOG_YEAR} cannot be accepted. "
            f"The minimum archival backlog year for the Municipal Engineering Office is {MINIMUM_BACKLOG_YEAR}."
        )
    return True

def validate_document_file(file):
    """
    Validate that the uploaded attachment is strictly a PDF document (.pdf),
    does not exceed 50MB, and is free of malware.
    Only verified, non-editable PDF files are accepted for archival storage.
    """
    # Extension validation - strictly PDF only
    ext = os.path.splitext(file.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError("Only verified PDF documents (.pdf) are accepted for archival in eTala.")

    # MIME type validation
    allowed_mime_types = [
        'application/pdf', 'application/x-pdf', 'application/acrobat', 
        'applications/vnd.pdf', 'text/pdf', 'text/x-pdf'
    ]
    if hasattr(file, 'content_type') and file.content_type:
        ct = file.content_type.lower()
        if ct not in allowed_mime_types:
            raise ValidationError("Invalid file content type. Only PDF documents (.pdf) are accepted.")

    # Size validation (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    if file.size > max_size:
        raise ValidationError("File exceeds 50MB limit. Please compress and re-upload.")

    # Virus scan validation
    virus_scan_file(file)


def validate_violation_evidence_file(file):
    """
    Validate that an attachment uploaded during Notice of Violation / Illegal Construction reporting
    is either a site photo (.jpg, .jpeg, .png, .webp) or a Notice of Violation document (.pdf),
    does not exceed 50MB, and passes security checks.
    Official engineering records remain strictly PDF-only.
    """
    ext = os.path.splitext(file.name)[1].lower()
    allowed_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
    if ext not in allowed_exts:
        raise ValidationError(
            "Invalid file format. For violation reports, please attach site photos (JPG, PNG, WEBP) "
            "or a Notice of Violation PDF document."
        )

    # MIME type validation
    allowed_mime_types = [
        'application/pdf', 'application/x-pdf', 'application/acrobat', 
        'applications/vnd.pdf', 'text/pdf', 'text/x-pdf',
        'image/jpeg', 'image/pjpeg', 'image/png', 'image/webp', 'image/x-png'
    ]
    if hasattr(file, 'content_type') and file.content_type:
        ct = file.content_type.lower()
        if ct not in allowed_mime_types:
            raise ValidationError(
                "Invalid file content type. Only photos (JPG, PNG, WEBP) and PDF documents are supported for violation reporting."
            )

    # Size validation (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    if file.size > max_size:
        raise ValidationError("File exceeds 50MB limit. Please compress and re-upload.")

    # Virus scan validation
    virus_scan_file(file)

def sanitize_input(value):
    """Sanitize user input to prevent XSS by stripping tags and escaping HTML."""
    if not value:
        return value
    clean_tags = re.compile(r'<[^>]*>')
    stripped = re.sub(clean_tags, '', str(value)).strip()
    return escape(stripped)


def validate_password_strength(password, min_length=8, require_complexity=False):
    """Validate password requirements (standard: minimum 8 characters)."""
    if not password or len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    if require_complexity:
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number."
    return True, None



