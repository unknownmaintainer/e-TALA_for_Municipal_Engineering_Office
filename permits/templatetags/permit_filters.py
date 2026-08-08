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
    """Safely retrieves the .url property of a FieldFile without raising Cloudinary/Storage exceptions."""
    if not file_field:
        return ''
    try:
        return file_field.url
    except Exception:
        return ''



