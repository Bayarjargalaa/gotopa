from .models import PageContent
from .menu_config import get_user_menu, get_header_menu, HEADER_MENU

def page_content_processor(request):
    """
    Бүх template-д page_contents автоматаар дамжуулах context processor
    """
    contents = {}
    all_contents = PageContent.objects.filter(is_active=True)
    
    for content in all_contents:
        contents[content.key] = content.content
    
    # Хэрэглэгчийн цэснүүд
    user_menu = []
    header_menu = []
    
    if request.user.is_authenticated:
        user_menu = get_user_menu(request.user)
        header_menu = get_header_menu(request.user)
    else:
        # Нэвтрээгүй хэрэглэгчдэд зөвхөн public items (permissions хоосон)
        for item in HEADER_MENU:
            perms = item.get('permissions', [])
            # Эрх хоосон бол public item
            if not perms:
                if item.get('is_dropdown') and 'items' in item:
                    # Dropdown бол sub-items-ийг шүүх
                    filtered_items = [sub for sub in item['items'] if not sub.get('permissions', [])]
                    if filtered_items:
                        item_copy = item.copy()
                        item_copy['items'] = filtered_items
                        header_menu.append(item_copy)
                else:
                    header_menu.append(item)
    
    return {
        'page_contents': contents,
        'can_edit_content': (
            request.user.is_authenticated and 
            request.user.is_staff and 
            (request.user.is_superuser or request.user.groups.filter(name='Content Editor').exists())
        ),
        'user_menu': user_menu,  # Sidebar menu
        'header_menu': header_menu,  # Header navigation
    }
