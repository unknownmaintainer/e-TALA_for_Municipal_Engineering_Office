from django import template
from django.utils.safestring import mark_safe

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


def _sentence(actor, verb_phrase):
    """Combines actor (e.g. <strong>Mardion Fuerte</strong> ) with an action verb phrase."""
    if not actor:
        if verb_phrase and verb_phrase[0].islower():
            return mark_safe(verb_phrase[0].upper() + verb_phrase[1:])
        return mark_safe(verb_phrase)

    raw_actor_name = re.sub(r'<[^>]+>', '', actor).strip().lower()
    clean_verb = verb_phrase.strip()
    # If the text already starts with the actor name, avoid repeating it
    if clean_verb.lower().startswith(raw_actor_name):
        return mark_safe(clean_verb)

    if clean_verb and clean_verb[0].isupper():
        clean_verb = clean_verb[0].lower() + clean_verb[1:]
    return mark_safe(f"{actor}{clean_verb}")


@register.filter(name='clean_audit_action')
def clean_audit_action(action, user=None):
    """
    Formats audit log text into natural, sentence-like activity updates (similar to modern social/activity feeds)
    with the actor's name and highlighted targets for maximum clarity.
    """
    if not action:
        return ''
    s = str(action).strip()
    
    # Clean encoding artifacts, corrupt characters, and normalize bullet/dot separators
    s = s.replace(chr(183), ' &middot; ').replace('\ufffd', ' &middot; ').replace(' · ', ' &middot; ')
    s = re.sub(r'\s*&middot;\s*', ' &middot; ', s)

    # Skip internal notification markers
    if s.startswith(('NOTIF_READ:', 'NOTIF_DELETED:')):
        return ''
    
    # Strip any obsolete/legacy (Status: ...) or (Compliance: ...) suffixes
    s = re.sub(r"\s*\((?:Status|Compliance):\s*[^)]+\)", "", s, flags=re.IGNORECASE).strip()

    # Determine actor prefix
    actor = ""
    if user:
        if isinstance(user, str):
            uname = user.strip()
        else:
            uname = getattr(user, 'full_name', None) or getattr(user, 'username', None) or str(user)
        if uname:
            actor = f"<strong>{uname}</strong> "
    else:
        # Automated background tasks or cron services have no user
        actor = "<strong>Scheduled System Task</strong> "

    # 0. Errors, Failures & Security Alerts (Direct, clear, and visible for admin awareness)
    if any(s.lower().startswith(k) for k in ['failed', 'error', 'system error', 'access denied', 'restricted', 'blocked', 'account locked']):
        s = re.sub(r"\b[A-Za-z]:\\[^:\s]+", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        if 'permanently locked out' in s.lower() or 'locked out permanently' in s.lower():
            return mark_safe("Account was permanently locked out after 10 failed login attempts")
        if s.startswith('Blocked login access for account:'):
            acc = s.split('account:', 1)[-1].strip().strip('\'"')
            return _sentence(actor, f"Blocked login access for account <strong>{acc}</strong>")
        if s.startswith('Restored login access for account:'):
            acc = s.split('account:', 1)[-1].strip().strip('\'"')
            return _sentence(actor, f"Restored login access for account <strong>{acc}</strong>")
        if s.startswith('Blocked device access'):
            return mark_safe("Restricted device access due to suspicious login attempts")
        if s.startswith('Blocked IP address:'):
            ip = s.split('address:', 1)[-1].strip()
            return _sentence(actor, f"Blocked access for IP address <strong>{ip}</strong>")
        return mark_safe(s)
    
    # 1. Clean email notifications
    if 'Triggered Document Expiry Email Alerts' in s or 'Dispatched document expiry' in s:
        return _sentence(actor, 'Dispatched document expiry email notifications')

    # 2. Automated Backups & System Exports
    if 'Automated System Backup' in s:
        m = re.search(r"\((\d+)\s*records", s)
        cnt = f"{int(m.group(1)):,} records" if m else "system records"
        return _sentence(actor, f"Completed automated system backup of <strong>{cnt}</strong>")
    if 'Exported complete municipal archive backup' in s or 'Exported Complete System Archive' in s:
        return _sentence(actor, 'Exported complete municipal archive backup package (.ZIP)')
    if 'Exported full database backup' in s or 'Exported data-only' in s:
        return _sentence(actor, 'Exported database records backup (JSON)')
        
    # 3. User Password & Security Actions
    if 'Reset password for user' in s:
        m = re.search(r"['\"]([^'\"]+)['\"]", s)
        target_user = m.group(1) if m else "user"
        return _sentence(actor, f"Reset password for user <strong>{target_user}</strong>")
    if s in ['Changed password', 'Changed account password']:
        return _sentence(actor, 'Changed account security password')
    if 'Account locked out permanently' in s:
        return mark_safe('Account was permanently locked out after 10 failed login attempts')
    if 'Blocked device access' in s:
        return mark_safe('Restricted device access due to suspicious login attempts')
    if 'Blocked login access for account:' in s:
        acc = s.split('account:', 1)[-1].strip().strip('\'"')
        return _sentence(actor, f"Blocked login access for account <strong>{acc}</strong>")
    if 'Restored login access for account:' in s:
        acc = s.split('account:', 1)[-1].strip().strip('\'"')
        return _sentence(actor, f"Restored login access for account <strong>{acc}</strong>")
    if 'Permanently deleted unused user account' in s or 'Permanently deleted user account' in s:
        m = re.search(r"['\"]([^'\"]+)['\"]", s)
        user_str = m.group(1) if m else ""
        return _sentence(actor, f"Permanently deleted user account for <strong>{user_str}</strong>")
    if 'Toggled user' in s:
        m = re.search(r"['\"]([^'\"]+)['\"]", s)
        user_str = m.group(1) if m else ""
        if 'deactivated' in s.lower() or 'inactive' in s.lower():
            return _sentence(actor, f"Deactivated user account for <strong>{user_str}</strong>")
        elif 'activated' in s.lower() or 'active' in s.lower():
            return _sentence(actor, f"Activated user account for <strong>{user_str}</strong>")

    # 4. User creation
    if 'Created new' in s and 'account:' in s:
        m = re.search(r"Created new (\w+) account:\s*['\"]?([^'\"\(]+)", s)
        if m:
            role = m.group(1).title()
            name = m.group(2).strip()
            return _sentence(actor, f"Created a new <strong>{role}</strong> account for <strong>{name}</strong>")
    if s.startswith('Created user ') and ' with role ' in s:
        m = re.search(r"Created user '([^']+)'", s)
        role_m = re.search(r"with role '([^']+)'", s)
        user_str = m.group(1) if m else ''
        role_str = role_m.group(1).title() if role_m else 'Staff'
        return _sentence(actor, f"Created a new <strong>{role_str}</strong> account for <strong>{user_str}</strong>")

    # 5. Trash & Restores (Conversational Facebook-style sentence)
    if s.startswith("Moved to Trash:"):
        inner = s.replace("Moved to Trash:", "").strip().strip("'\"")
        if (inner.startswith('[') and inner.endswith(']')) or (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
            inner = inner[1:-1].strip()
        if inner.lower().startswith('violation:'):
            v_desc = inner[10:].strip()
            inner = f"violation case {v_desc}" if v_desc else "violation case"
        return _sentence(actor, f"Moved <strong>{inner}</strong> to trash")
    if s.startswith("Restored:"):
        inner = s.replace("Restored:", "").strip().strip("'\"")
        if (inner.startswith('[') and inner.endswith(']')) or (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
            inner = inner[1:-1].strip()
        if inner.lower().startswith('violation:'):
            v_desc = inner[10:].strip()
            inner = f"violation case {v_desc}" if v_desc else "violation case"
        return _sentence(actor, f"Restored <strong>{inner}</strong> from trash")
    if s.startswith('Batch Permanently Deleted'):
        m = re.search(r"\((\d+)\s*records", s)
        cnt = f"{m.group(1)} records" if m else "records"
        return _sentence(actor, f"Permanently deleted <strong>{cnt}</strong> from trash")

    # 6. Record Creations & Updates
    if s.startswith('Created ') and ' record:' in s:
        m = re.search(r"^Created (\w+) record:\s*['\"]?(.+?)['\"]?$", s)
        if m:
            rtype = m.group(1).lower()
            title = m.group(2).strip()
            return _sentence(actor, f"Created new {rtype} record <strong>{title}</strong>")
    if s.startswith('Updated ') and (' Project:' in s or ' Permit:' in s or ' Record:' in s):
        m = re.search(r"^Updated (\w+):\s*['\"]?(.+?)['\"]?$", s)
        if m:
            rtype = m.group(1).lower()
            title = m.group(2).strip()
            return _sentence(actor, f"Updated details for {rtype} <strong>{title}</strong>")

    # 7. Violations & Official Permits
    if 'Issued Official Permit #' in s:
        m = re.search(r"Issued Official Permit #([^\s]+)\s+for violation\s*['\"]?([^'\"\(]+)", s)
        if m:
            p_no = m.group(1).strip()
            title = m.group(2).strip().strip("'\"·- ")
            if '·' in title or '&middot;' in title:
                title = title.split('·')[-1].split('&middot;')[-1].strip()
            return _sentence(actor, f"Issued official permit <strong>#{p_no}</strong> for <strong>{title}</strong> (Case Resolved)")
        return _sentence(actor, "Issued official permit to resolve violation case")
    if s.startswith('Flagged Illegal Construction at Barangay') or s.startswith('Flagged Illegal Construction at Brgy'):
        m = re.search(r"Flagged Illegal Construction at (?:Barangay|Brgy\.?)\s*([^:]+):\s*(.+)", s, flags=re.IGNORECASE)
        if m:
            brgy = m.group(1).strip()
            title = m.group(2).strip().strip("'\"")
            return _sentence(actor, f"Flagged illegal construction <strong>{title}</strong> in <strong>Brgy. {brgy}</strong>")
    if 'Flagged as Illegal Construction' in s:
        return _sentence(actor, 'Flagged record as an illegal construction')
    if 'Unflagged Illegal Construction' in s or 'Removed Illegal Construction flag' in s:
        return _sentence(actor, 'Removed illegal construction flag from record')
    if 'Removed violation flag from record' in s:
        m = re.search(r"record\s*['\"]?([^'\"]+)['\"]?", s)
        title = m.group(1) if m else "record"
        return _sentence(actor, f"Removed violation flag from <strong>{title}</strong>")
    if 'Updated Illegal Construction Compliance to' in s or 'Updated violation status to' in s:
        m = re.search(r"for record\s*['\"]?([^'\"]+)['\"]?", s)
        title = m.group(1) if m else "record"
        return _sentence(actor, f"Updated violation compliance status for <strong>{title}</strong>")
    if 'Regularized incident case into' in s:
        m = re.search(r"into (.+)", s)
        target = m.group(1).strip() if m else "official record"
        return _sentence(actor, f"Regularized illegal construction into official record <strong>{target}</strong>")

    # 8. Document uploads/deletions
    if 'Uploaded document' in s and ' for ' in s:
        m = re.search(r"for\s*['\"]?([^'\"]+?)['\"]?\s*in\s*['\"]?([^'\"]+?)['\"]?$", s)
        if m:
            doc_slot = re.sub(r"^[A-Z0-9]+\s*[-–—:]\s*", "", m.group(1).strip())
            return _sentence(actor, f"Uploaded document <strong>{doc_slot}</strong>")
        m2 = re.search(r"for\s*['\"]?([^'\"]+?)['\"]?$", s)
        if m2:
            doc_slot = re.sub(r"^[A-Z0-9]+\s*[-–—:]\s*", "", m2.group(1).strip())
            return _sentence(actor, f"Uploaded document <strong>{doc_slot}</strong>")
    if s.startswith("Uploaded:") and " for " in s:
        m = re.search(r"Uploaded:\s*(.+?)\s*for\s*(.+?)(?:\s*[—–-]\s*(.+))?$", s)
        if m:
            doc_type = re.sub(r"^[A-Z]+\s*[-–—]\s*", "", m.group(1).strip())
            return _sentence(actor, f"Uploaded document <strong>{doc_type}</strong>")
    if s.startswith("Deleted:") and " from " in s:
        m = re.search(r"Deleted:\s*(.+?)\s*from\s*['\"]?(.+?)['\"]?$", s)
        if m:
            doc_name = re.sub(r"^[A-Z]+\s*[-–—]\s*", "", m.group(1).strip())
            return _sentence(actor, f"Deleted document <strong>{doc_name}</strong>")
    if "Uploaded" in s and "file(s)" in s:
        m = re.search(r"Uploaded (\d+) new file\(s\).*? for (.+?)(?: in ['\"].+?['\"])?$", s)
        if m:
            c = m.group(1)
            target = re.sub(r"^[A-Z0-9]+\s*[-–—:]\s*", "", m.group(2).strip())
            return _sentence(actor, f"Uploaded <strong>{c} files</strong> for <strong>{target}</strong>")
    if s.startswith("Deleted all attached files") or "Deleted all attached files (" in s:
        m = re.search(r"Deleted all attached files(?: \((\d+ files?|\d+)\))?\s*for (.+?)(?: from ['\"].+?['\"])?$", s)
        if m:
            target = m.group(2).strip()
            return _sentence(actor, f"Deleted all attached files for <strong>{target}</strong>")

    # 9. Checklist Requirements & Templates
    if "marked as N/A (waived)" in s:
        m = re.search(r"Requirement\s*['\"]?([^'\"]+)['\"]?", s)
        req_name = m.group(1) if m else "requirement"
        return _sentence(actor, f"Marked requirement <strong>{req_name}</strong> as N/A (waived)")
    if "marked as required" in s:
        m = re.search(r"Requirement\s*['\"]?([^'\"]+)['\"]?", s)
        req_name = m.group(1) if m else "requirement"
        return _sentence(actor, f"Marked requirement <strong>{req_name}</strong> as required")
    if s.startswith('Created checklist template:'):
        tmpl = s.split(':', 1)[-1].strip().strip("'\"")
        return _sentence(actor, f"Created checklist template <strong>{tmpl}</strong>")
    if s.startswith('Updated checklist template details:'):
        tmpl = s.split(':', 1)[-1].strip().strip("'\"")
        return _sentence(actor, f"Updated checklist template details for <strong>{tmpl}</strong>")
    if 'Added ' in s and ' to template ' in s:
        m = re.search(r"Added \w+ '([^']+)' to template '([^']+)'", s)
        if m:
            return _sentence(actor, f"Added item <strong>{m.group(1)}</strong> to template <strong>{m.group(2)}</strong>")
    if 'Updated requirement ' in s and ' to ' in s:
        m = re.search(r"to '([^']+)'", s)
        if m:
            return _sentence(actor, f"Updated requirement item to <strong>{m.group(1)}</strong>")
    if 'Deleted requirement ' in s and ' from template' in s:
        m = re.search(r"Deleted requirement '([^']+)'", s)
        if m:
            return _sentence(actor, f"Deleted requirement <strong>{m.group(1)}</strong> from template")

    # 10. Feedback & Email updates
    if 'Submitted' in s and 'Feedback' in s:
        return _sentence(actor, "Submitted system feedback to administrators")
    if "Work email address updated from" in s and "to" in s:
        m = re.search(r"to\s+([^\s]+)\s+via OTP", s)
        if m:
            return _sentence(actor, f"Updated work email address to <strong>{m.group(1)}</strong>")
        return _sentence(actor, "Updated work email address")

    # Final polish: Remove quotes and normalize dashes
    s = s.replace('—', ' &middot; ').replace('–', ' &middot; ')
    s = re.sub(r"'([^']+)'", r"<strong>\1</strong>", s)
    return _sentence(actor, s.strip())


@register.filter(name='is_audit_error')
def is_audit_error(action):
    """Checks if an audit action represents a system error, failure, or security alert."""
    if not action:
        return False
    a = str(action).lower()
    return any(k in a for k in ['error', 'failed', 'blocked', 'denied', 'restricted', 'locked out', 'lockout', 'warning'])


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


@register.filter(name='clean_resolved_description')
def clean_resolved_description(description, record=None):
    """
    Cleans up auto-generated boilerplate violation text from remarks when a record is resolved.
    If the description only contains boilerplate violation tags, returns an empty string.
    """
    if not description:
        return ''
    desc_str = str(description).strip()
    if not desc_str:
        return ''
    
    parts = [p.strip() for p in desc_str.split('•') if p.strip()]
    cleaned_parts = []
    for part in parts:
        lower_p = part.lower()
        if lower_p.startswith('violation:') or lower_p.startswith('building type:') or lower_p.startswith('unpermitted construction'):
            continue
        cleaned_parts.append(part)
    
    return ' • '.join(cleaned_parts)


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
    elif fn.endswith(('.dwg', '.dxf')):
        return 'fa-solid fa-compass-drafting text-warning'
    elif fn.endswith(('.zip', '.rar', '.7z', '.tar', '.gz')):
        return 'fa-solid fa-file-zipper text-warning'
    return 'fa-solid fa-file text-secondary'








