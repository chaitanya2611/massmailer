from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Usage: {{ some_dict|get_item:some_key }} — Django templates can't do dict[var] directly."""
    if not dictionary:
        return ""
    return dictionary.get(key, "")
