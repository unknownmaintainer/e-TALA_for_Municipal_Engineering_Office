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
    """Formats audit log text into concise, professional, and unambiguous municipal actions."""
    if not action:
        return ''
    s = str(action).strip()
    
    # Clean email expiry disclaimers to simple notification action
    if 'Triggered Document Expiry Email Alerts' in s:
        return 'Dispatched document expiry email notifications'
        
    # Clean user permanent deletion wording
    if 'Permanently deleted unused user account' in s:
        m = re.search(r"'([^']+)'", s)
        user_str = f" {m.group(1)}" if m else ""
        return f"Deleted user account{user_str}"
        
    # Clean user status toggle wording
    if 'Toggled user' in s:
        m = re.search(r"'([^']+)'", s)
        user_str = f" {m.group(1)}" if m else ""
        if 'deactivated' in s:
            return f"Deactivated user account{user_str}"
        elif 'activated' in s:
            return f"Activated user account{user_str}"
            
    # Clean user creation wording
    if s.startswith('Created user ') and ' with role ' in s:
        m = re.search(r"Created user '([^']+)'", s)
        role_m = re.search(r"with role '([^']+)'", s)
        user_str = m.group(1) if m else ''
        role_str = role_m.group(1).title() if role_m else 'Staff'
        return f"Created {role_str} account for {user_str}"
        
    # Clean user profile update wording
    if s.startswith('Updated user profile for '):
        m = re.search(r"'([^']+)'", s)
        user_str = f" {m.group(1)}" if m else ""
        return f"Updated user profile for {user_str}".strip()

    # Clean 'Moved to Trash: ...'
    if s.startswith("Moved to Trash:"):
        inner = s.replace("Moved to Trash:", "").strip().strip("'\"")
        return f"Moved to Trash: {inner}"

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
    [{'label': 'Violation', 'value': 'No Building Permit'}, ...]
    If no ':' is found, returns a single item list [{'label': '', 'value': text}].
    """
    if not text:
        return []
    import html
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    parsed = []
    
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            lbl = html.unescape(parts[0].strip())
            val = html.unescape(parts[1].strip())
            # Clean up robotic labels to simple municipal terms
            if lbl.lower() == 'violation category':
                lbl = 'Violation Type'
            elif lbl.lower() == 'inspection findings':
                lbl = 'Inspection Notes'
            if val:
                parsed.append({'label': lbl, 'value': val})
        else:
            clean_line = html.unescape(line)
            if parsed:
                parsed[-1]['value'] += '\n' + clean_line
            else:
                parsed.append({'label': '', 'value': clean_line})
                
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
    invalid_placeholders = [',,', ',', ', ', 'N/A', 'n/a', 'None', 'none', '—', '-', 'undefined', 'null']
    if name_str in invalid_placeholders:
        return False
    return True


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







