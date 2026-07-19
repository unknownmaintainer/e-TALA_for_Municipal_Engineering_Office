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

