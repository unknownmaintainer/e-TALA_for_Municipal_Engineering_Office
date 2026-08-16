from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(dictionary, key):
    """Retrieves a value from a dictionary given its key."""
    if not isinstance(dictionary, dict):
        return ''
    return dictionary.get(key, '')


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
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    parsed = []
    
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            lbl = parts[0].strip()
            val = parts[1].strip()
            # Clean up robotic labels to simple municipal terms
            if lbl.lower() == 'violation category':
                lbl = 'Violation Type'
            elif lbl.lower() == 'inspection findings':
                lbl = 'Inspection Notes'
            parsed.append({'label': lbl, 'value': val})
        else:
            if parsed:
                parsed[-1]['value'] += '\n' + line
            else:
                parsed.append({'label': '', 'value': line})
                
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






