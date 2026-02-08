from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag(takes_context=True)
def editable(context, key, default=""):
    """
    Админ эрхтэй хэрэглэгч нэвтэрсэн үед засах товчтой wrapper үүсгэнэ
    
    Ашиглалт:
        {% editable 'home_hero_title' "Анхдагч текст" %}
    """
    request = context.get('request')
    page_contents = context.get('page_contents', {})
    can_edit = context.get('can_edit_content', False)
    
    # Агуулга авах
    display_content = page_contents.get(key, default)
    
    # Админ эрхтэй бол засах товчтой wrapper
    if can_edit:
        return mark_safe(
            f'<span class="editable-content" data-key="{key}" data-editable="true">'
            f'{display_content}'
            f'<button class="edit-btn" onclick="editContent(\'{key}\', event)" '
            f'title="Засах" aria-label="Агуулга засах">'
            f'<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
            f'd="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />'
            f'</svg>'
            f'</button>'
            f'</span>'
        )
    else:
        # Энгийн хэрэглэгчид зөвхөн агуулга харуулна
        return mark_safe(display_content)


@register.filter
def get_item(dictionary, key):
    """
    Dictionary-с key-ээр утга авах filter
    
    Ашиглалт:
        {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
