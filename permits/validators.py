from django.core.exceptions import ValidationError
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
    """Validate that file is PDF, JPG, or PNG, does not exceed 10MB, and is free of malware."""
    # Extension validation
    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.docx']
    if ext not in allowed_extensions:
        raise ValidationError("Only PDF, JPG, PNG, and DOCX files are accepted.")

    # MIME type validation
    allowed_mime_types = [
        'application/pdf', 'image/jpeg', 'image/png', 'image/jpg',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]
    if hasattr(file, 'content_type') and file.content_type not in allowed_mime_types:
        raise ValidationError("Invalid file content type. Only PDF, JPG, PNG, and DOCX are allowed.")

    # Size validation
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if file.size > max_size:
        raise ValidationError("File exceeds 10MB. Please compress and re-upload.")

    # Virus scan validation
    virus_scan_file(file)

def sanitize_input(value):
    """Sanitize user input to prevent XSS."""
    if not value:
        return value
    clean = re.compile('<.*?>')
    return re.sub(clean, '', value).strip()

