from .models import PageContent

def page_content_processor(request):
    """
    Бүх template-д page_contents автоматаар дамжуулах context processor
    """
    contents = {}
    all_contents = PageContent.objects.filter(is_active=True)
    
    for content in all_contents:
        contents[content.key] = content.content
    
    return {
        'page_contents': contents,
        'can_edit_content': (
            request.user.is_authenticated and 
            request.user.is_staff and 
            (request.user.is_superuser or request.user.groups.filter(name='Content Editor').exists())
        )
    }
