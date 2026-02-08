"""Custom template filters"""
from django import template
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get item from dictionary
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    
    # Handle string keys that need to be converted to int
    if isinstance(key, str) and key.isdigit():
        key = int(key)
    
    return dictionary.get(key)


@register.filter
def jsonify(value):
    """
    Convert Python object to JSON string
    Usage: {{ mydata|jsonify }}
    """
    return json.dumps(value, ensure_ascii=False)
