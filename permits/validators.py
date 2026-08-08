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

def validate_document_file(file):
    """Validate that file is PDF or scanned image (JPG, PNG, WEBP), does not exceed 10MB, and is free of malware."""
    # Extension validation
    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
    if ext not in allowed_extensions:
        raise ValidationError("Only PDF document files and scanned image files (JPG, PNG, WEBP) are accepted.")

    # MIME type validation
    allowed_mime_types = [
        'application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'image/webp',
        'image/pjpeg', 'image/x-png'
    ]
    if hasattr(file, 'content_type') and file.content_type and file.content_type.lower() not in allowed_mime_types:
        raise ValidationError("Invalid file content type. Only PDF document files and scanned images are allowed.")

    # Size validation
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if file.size > max_size:
        raise ValidationError("File exceeds 10MB. Please compress and re-upload.")

    # Virus scan validation
    virus_scan_file(file)

def sanitize_input(value):
    """Sanitize user input to prevent XSS by stripping tags and escaping HTML."""
    if not value:
        return value
    clean_tags = re.compile(r'<[^>]*>')
    stripped = re.sub(clean_tags, '', str(value)).strip()
    return escape(stripped)



