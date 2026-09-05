from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(dictionary, key):
    """Retrieves a value from a dictionary given its key, matching both int and str representations."""
    if not isinstance(dictionary, dict) or key is None:
        return ''
    if key in dictionary:
        return dictionary[key]
    str_k = str(key)
    if str_k in dictionary:
        return dictionary[str_k]
    try:
        int_k = int(str_k)
        if int_k in dictionary:
            return dictionary[int_k]
    except (ValueError, TypeError):
        pass
    return ''


import re

@register.filter(name='clean_req_name')
def clean_req_name(value):
    """Strips legacy (a.1), (a.2), etc. numbering annotations from requirement names."""
    if not value:
        return ''
    return re.sub(r'\s*\([a-z]\.\d+\)', '', str(value)).strip()


@register.filter(name='clean_audit_action')
def clean_audit_action(action):
    """Formats audit log text into concise, professional, and easily understandable municipal actions."""
    if not action:
        return ''
    s = str(action).strip()
    
    # Strip any obsolete/legacy (Status: ...) or (Compliance: ...) suffixes
    s = re.sub(r"\s*\((?:Status|Compliance):\s*[^)]+\)", "", s, flags=re.IGNORECASE).strip()
    
    # 1. Clean email notifications
    if 'Triggered Document Expiry Email Alerts' in s or 'Dispatched document expiry' in s:
        return 'Dispatched Document Expiry Email Alerts'
        
    # 2. Clean user deletion & toggle wording
    if 'Permanently deleted unused user account' in s:
        m = re.search(r"'([^']+)'", s)
        user_str = f": {m.group(1)}" if m else ""
        return f"Deleted User Account{user_str}"
    if 'Toggled user' in s:
        m = re.search(r"'([^']+)'", s)
        user_str = f": {m.group(1)}" if m else ""
        if 'deactivated' in s.lower() or 'inactive' in s.lower():
            return f"Deactivated Account{user_str}"
        elif 'activated' in s.lower() or 'active' in s.lower():
            return f"Activated Account{user_str}"
            
    # 3. Clean user creation wording
    if 'Created new' in s and 'account:' in s:
        m = re.search(r"Created new (\w+) account:\s*['\"]?([^'\"\(]+)", s)
        if m:
            role = m.group(1).title()
            name = m.group(2).strip()
            return f"Created {role} Account: {name}"
    if s.startswith('Created user ') and ' with role ' in s:
        m = re.search(r"Created user '([^']+)'", s)
        role_m = re.search(r"with role '([^']+)'", s)
        user_str = m.group(1) if m else ''
        role_str = role_m.group(1).title() if role_m else 'Staff'
        return f"Created {role_str} Account: {user_str}"
        
    # 4. Clean password actions
    if 'Reset password for user' in s:
        m = re.search(r"'([^']+)'", s)
        user_str = f": {m.group(1)}" if m else ""
        return f"Reset Password for User{user_str}"
    if s in ['Changed password', 'Changed account password']:
        return 'Changed Account Password'

    # 5. Clean Record Creations & Updates
    if s.startswith('Created ') and ' record:' in s:
        s = re.sub(r"^Created (\w+) record:\s*['\"]?(.+?)['\"]?$", r"Created \1: \2", s)
    if s.startswith('Updated ') and (' Project:' in s or ' Permit:' in s or ' Record:' in s):
        s = re.sub(r"^Updated (\w+):\s*['\"]?(.+?)['\"]?$", r"Updated \1: \2", s)

    # 6. Clean Trash & Restores
    if s.startswith("Moved to Trash:"):
        inner = s.replace("Moved to Trash:", "").strip().strip("'\"")
        return f"Moved to Trash: {inner}"
    if s.startswith("Restored:"):
        inner = s.replace("Restored:", "").strip().strip("'\"")
        return f"Restored from Trash: {inner}"

    # 7. Clean Violations & Illegal Constructions (Legacy and Modern)
    if s.startswith('Flagged Illegal Construction at Barangay') or s.startswith('Flagged Illegal Construction at Brgy'):
        m = re.search(r"Flagged Illegal Construction at (?:Barangay|Brgy\.?)\s*([^:]+):\s*(.+)", s, flags=re.IGNORECASE)
        if m:
            brgy = m.group(1).strip()
            title = m.group(2).strip().strip("'\"")
            return f"Flagged Illegal Construction: {title} (Brgy. {brgy})"
    if 'Flagged as Illegal Construction' in s:
        return 'Flagged as Illegal Construction'
    if 'Unflagged Illegal Construction' in s or 'Removed Illegal Construction flag' in s:
        return 'Removed Illegal Construction Flag'
    if 'Removed violation flag from record' in s:
        m = re.search(r"record\s*['\"]?([^'\"]+)['\"]?", s)
        title = f": {m.group(1)}" if m else ""
        return f"Removed Violation Flag{title}"
    if 'Updated Illegal Construction Compliance to' in s or 'Updated violation status to' in s:
        m = re.search(r"for record\s*['\"]?([^'\"]+)['\"]?", s)
        title = f": {m.group(1)}" if m else ""
        return f"Updated Violation Status{title}"
    if 'Issued Official Permit #' in s:
        m = re.search(r"Issued Official Permit #([^\s]+)\s+for violation\s*['\"]?([^'\"]+)['\"]?", s)
        if m:
            return f"Issued Permit #{m.group(1)}: {m.group(2)}"
        return "Issued Official Permit for Violation"
    if 'Regularized incident case into' in s:
        m = re.search(r"into (.+)", s)
        return f"Regularized Record: {m.group(1)}" if m else "Regularized Illegal Construction"
    if 'Reported violation at' in s:
        m = re.search(r"Reported violation at (?:Barangay|Brgy\.?)\s*([^:]+):\s*['\"]?([^'\"]+)['\"]?(?:\s*[—–-]\s*|\s*:\s*)(.+)", s)
        if m:
            brgy = m.group(1).strip()
            title = m.group(2).strip()
            return f"Reported Violation: {title} (Brgy. {brgy})"

    # 8. Clean Requirement N/A & Waivers
    if "marked as N/A (waived)" in s:
        m = re.search(r"Requirement\s*['\"]?([^'\"]+)['\"]?", s)
        req_name = f": {m.group(1)}" if m else ""
        return f"Marked Requirement as N/A{req_name}"
    if "marked as required" in s:
        m = re.search(r"Requirement\s*['\"]?([^'\"]+)['\"]?", s)
        req_name = f": {m.group(1)}" if m else ""
        return f"Marked Requirement as Required{req_name}"

    # 9. Clean Checklist Templates
    if s.startswith('Created checklist template:'):
        tmpl = s.split(':', 1)[-1].strip().strip("'\"")
        return f"Created Template: {tmpl}"
    if s.startswith('Updated checklist template details:'):
        tmpl = s.split(':', 1)[-1].strip().strip("'\"")
        return f"Updated Template: {tmpl}"
    if 'Added ' in s and ' to template ' in s:
        m = re.search(r"Added \w+ '([^']+)' to template '([^']+)'", s)
        if m:
            return f"Added Template Item: {m.group(1)}"
    if 'Updated requirement ' in s and ' to ' in s:
        m = re.search(r"to '([^']+)'", s)
        if m:
            return f"Updated Template Item: {m.group(1)}"
    if 'Deleted requirement ' in s and ' from template' in s:
        m = re.search(r"Deleted requirement '([^']+)'", s)
        if m:
            return f"Deleted Template Item: {m.group(1)}"

    # 10. Clean Barangay Management
    if s.startswith('Created Barangay '):
        name = s.replace('Created Barangay', '').strip().strip("'\"")
        return f"Created Barangay: {name}"
    if s.startswith('Updated Barangay '):
        name = s.replace('Updated Barangay', '').strip().strip("'\"")
        return f"Updated Barangay: {name}"
    if s.startswith('Deleted Barangay '):
        name = s.replace('Deleted Barangay', '').strip().strip("'\"")
        return f"Deleted Barangay: {name}"

    # 11. Clean Database Backup & Restore
    if 'Exported full database backup' in s:
        return 'Exported Database Backup (JSON)'
    if 'Restored' in s and 'from backup file' in s:
        m = re.search(r"backup file '([^']+)'", s)
        fname = f" ({m.group(1)})" if m else ""
        return f"Restored Database from Backup{fname}"
    if s.startswith('Updated office settings:'):
        return 'Updated Office Settings'

    # 12. Clean Document uploads/deletions (Legacy & Modern)
    if s.startswith("Uploaded:") and " for " in s:
        m = re.search(r"Uploaded:\s*(.+?)\s*for\s*(.+?)(?:\s*[—–-]\s*(.+))?$", s)
        if m:
            doc_type = m.group(1).strip()
            # Clean abbreviations with hyphens e.g. "FSIC - Fire Safety..." -> "Fire Safety..."
            doc_type = re.sub(r"^[A-Z]+\s*[-–—]\s*", "", doc_type)
            return f"Uploaded Document: {doc_type}"
    if s.startswith("Deleted:") and " from " in s:
        m = re.search(r"Deleted:\s*(.+?)\s*from\s*['\"]?(.+?)['\"]?$", s)
        if m:
            doc_name = m.group(1).strip()
            doc_name = re.sub(r"^[A-Z]+\s*[-–—]\s*", "", doc_name)
            return f"Deleted Document: {doc_name}"
    if "Uploaded" in s and "file(s)" in s:
        m = re.search(r"Uploaded (\d+) new file\(s\).*? for (.+?)(?: in ['\"].+?['\"])?$", s)
        if m:
            c = m.group(1)
            target = m.group(2).strip()
            return f"Uploaded {c} file{'s' if c != '1' else ''} for {target}"
    if s.startswith("Deleted all attached files") or "Deleted all attached files (" in s:
        m = re.search(r"Deleted all attached files(?: \((\d+ files?|\d+)\))?\s*for (.+?)(?: from ['\"].+?['\"])?$", s)
        if m:
            qty = f" ({m.group(1)})" if m.group(1) else ""
            target = m.group(2).strip()
            return f"Deleted attached files{qty} for {target}"

    # 13. Clean Email updates
    if "Work email address updated from" in s and "to" in s:
        m = re.search(r"to\s+([^\s]+)\s+via OTP", s)
        if m:
            return f"Updated Work Email: {m.group(1)}"
        return "Updated Work Email"

    # Final polish: Remove all em-dashes (—), en-dashes (–), and stray ' - ' dividers
    s = s.replace('—', ': ').replace('–', ': ')
    s = re.sub(r"\s+-\s+", ": ", s)
    # General cleanup of surrounding quotes for cleaner human reading
    s = re.sub(r"'([^']+)'", r"\1", s)
    return s


@register.filter(name='split')
def split(value, key):
    """Splits a string by a delimiter/key."""
    return value.split(key)


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """Updates request GET query parameters with new kwargs while maintaining active params."""
    request = context.get('request')
    if not request:
        return ''
    d = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None and v != '':
            d[k] = v
        elif k in d:
            del d[k]
    return d.urlencode()


@register.filter(name='safe_url')
def safe_url(file_field):
    """Safely retrieves the .url property of a FieldFile without raising Storage exceptions."""
    if not file_field:
        return ''
    try:
        return file_field.url
    except Exception:
        return ''


@register.filter(name='compact_number')
def compact_number(value):
    """
    Auto-formats numbers into clean, compact, human-readable formats:
    - 59 -> '59'
    - 9999 -> '9,999'
    - 12500 -> '12.5K'
    - 1238237 -> '1.2M' (or exact on hover)
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value

    if num >= 1_000_000_000:
        val = num / 1_000_000_000
        return f"{val:.1f}B".replace(".0B", "B")
    elif num >= 1_000_000:
        val = num / 1_000_000
        return f"{val:.1f}M".replace(".0M", "M")
    elif num >= 10_000:
        val = num / 1_000
        return f"{val:.1f}K".replace(".0K", "K")
    else:
        return str(int(num))


@register.filter(name='parse_notes')
def parse_notes(text):
    """
    Parses description/notes text containing 'Label: Value' lines into a list of dicts:
    [{'label': 'Violation Category', 'value': 'Safety & Hazard Violation'}, ...]
    Handles both newline-separated text and concatenated multi-field strings.
    """
    if not text:
        return []
    import html
    import re
    
    text_str = html.unescape(str(text).strip())
    
    # Split on newlines OR on concatenated known field prefixes
    split_pattern = r'(?:\r?\n|(?<=[^\s:])\s*(?=(?:Violation Category|Violation Type|Violation|Structure Type|Building Type|Enforcement Action|Inspection Findings|Inspection Notes|Date Inspected|Inspection Date|Remarks|Notes)\s*:))'
    raw_lines = re.split(split_pattern, text_str, flags=re.IGNORECASE)
    
    parsed = []
    
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue
            
        if ':' in line:
            parts = line.split(':', 1)
            lbl = parts[0].strip()
            val = parts[1].strip()
            
            # Clean trailing punctuation and bullet separators
            val = re.sub(r'[\s•·\-,;]+$', '', val).strip()
            
            # Standardize labels
            lbl_lower = lbl.lower()
            if lbl_lower in ['violation category', 'violation', 'violation type']:
                lbl = 'Violation Category'
            elif lbl_lower in ['inspection findings', 'inspection note', 'inspection notes']:
                lbl = 'Inspection Findings'
            elif lbl_lower == 'enforcement action':
                lbl = 'Enforcement Action'
            elif lbl_lower in ['structure type', 'building type']:
                lbl = 'Structure Type'
            elif lbl_lower in ['date inspected', 'inspection date']:
                lbl = 'Date Inspected'
            elif lbl_lower in ['remarks', 'notes']:
                lbl = 'Remarks'
                
            if val:
                parsed.append({'label': lbl, 'value': val})
        else:
            line_clean = re.sub(r'[\s•·\-,;]+$', '', line).strip()
            if line_clean:
                if parsed:
                    parsed[-1]['value'] += '\n' + line_clean
                else:
                    parsed.append({'label': '', 'value': line_clean})
                
    return parsed


@register.filter(name='is_valid_applicant')
def is_valid_applicant(name):
    """Returns True if the string is a real applicant name and not a violation tag or invalid placeholder."""
    if not name:
        return False
    name_str = str(name).strip()
    if not name_str:
        return False
    if name_str.startswith('[') or 'Violation:' in name_str or 'Unpermitted' in name_str:
        return False
    invalid_placeholders = [',,', ',', ', ', 'N/A', 'n/a', 'None', 'none', '—', '-', 'undefined', 'null', 'under investigation', 'unspecified']
    if name_str.lower() in invalid_placeholders:
        return False
    return True


@register.filter(name='short_timesince')
def short_timesince(value):
    """Formats a datetime into a clean, compact time ago string like '18m ago', '2h ago', '3d ago', or 'Just now'."""
    if not value:
        return 'Just now'
    from django.utils import timezone
    import datetime
    try:
        now = timezone.now()
        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            diff = now.date() - value
            days = diff.days
            if days <= 0:
                return 'Today'
            elif days == 1:
                return '1d ago'
            elif days < 7:
                return f'{days}d ago'
            elif days < 30:
                return f'{days // 7}w ago'
            return value.strftime('%b %d')
        
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        diff = now - value
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return 'Just now'
        minutes = seconds // 60
        if minutes < 60:
            return f'{minutes}m ago'
        hours = minutes // 60
        if hours < 24:
            return f'{hours}h ago'
        days = hours // 24
        if days < 7:
            return f'{days}d ago'
        weeks = days // 7
        if weeks < 4:
            return f'{weeks}w ago'
        return value.strftime('%b %d')
    except Exception:
        return 'Just now'


@register.filter(name='file_icon_class')
def file_icon_class(filename):
    """Returns the appropriate FontAwesome icon class and color based on file extension."""
    if not filename:
        return 'fa-solid fa-file text-secondary'
    fn = str(filename).lower()
    if fn.endswith('.pdf'):
        return 'fa-solid fa-file-pdf text-danger'
    elif fn.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp', '.ico')):
        return 'fa-solid fa-file-image text-primary'
    elif fn.endswith(('.doc', '.docx')):
        return 'fa-solid fa-file-word text-primary'
    elif fn.endswith(('.xls', '.xlsx', '.csv')):
        return 'fa-solid fa-file-excel text-success'
    elif fn.endswith(('.zip', '.rar', '.7z', '.tar', '.gz')):
        return 'fa-solid fa-file-zipper text-warning'
    return 'fa-solid fa-file text-secondary'








