"""
Эрхийн удирдлагын view-үүд
Permission & Group Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q


@login_required
def permission_group_list(request):
    """Эрхийн бүлгүүдийн жагсаалт"""
    # Зөвхөн админ хандана
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч энэ хуудсанд хандах боломжтой.')
        return redirect('main:dashboard')
    
    groups = Group.objects.all().prefetch_related('permissions', 'user_set')
    
    context = {
        'groups': groups,
    }
    return render(request, 'main/permission_group_list.html', context)


@login_required
def permission_group_create(request):
    """Шинэ эрхийн бүлэг үүсгэх"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч энэ хуудсанд хандах боломжтой.')
        return redirect('main:dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        permission_ids = request.POST.getlist('permissions')
        
        if not name:
            messages.error(request, 'Бүлгийн нэр оруулна уу.')
        elif Group.objects.filter(name=name).exists():
            messages.error(request, f'"{name}" нэртэй бүлэг аль хэдийн байна.')
        else:
            # Бүлэг үүсгэх
            group = Group.objects.create(name=name)
            
            # Эрхүүд нэмэх
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            
            messages.success(request, f'✓ "{name}" бүлэг амжилттай үүсгэгдлээ. {len(permission_ids)} эрх нэмэгдлээ.')
            return redirect('main:permission_group_edit', group_id=group.id)
    
    # Бүх эрхүүд (main app-н)
    permissions = Permission.objects.filter(
        content_type__app_label='main'
    ).select_related('content_type').order_by('content_type__model', 'codename')
    
    context = {
        'permissions': permissions,
        'group': None,
    }
    return render(request, 'main/permission_group_form.html', context)


@login_required
def permission_group_edit(request, group_id):
    """Эрхийн бүлэг засах"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч энэ хуудсанд хандах боломжтой.')
        return redirect('main:dashboard')
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        permission_ids = request.POST.getlist('permissions')
        
        if not name:
            messages.error(request, 'Бүлгийн нэр оруулна уу.')
        elif Group.objects.filter(name=name).exclude(id=group_id).exists():
            messages.error(request, f'"{name}" нэртэй бүлэг аль хэдийн байна.')
        else:
            # Нэр шинэчлэх
            old_name = group.name
            group.name = name
            group.save()
            
            # Эрхүүд шинэчлэх
            if permission_ids:
                permissions = Permission.objects.filter(id__in=permission_ids)
                group.permissions.set(permissions)
            else:
                group.permissions.clear()
            
            messages.success(request, f'✓ "{old_name}" бүлэг шинэчлэгдлээ. {len(permission_ids)} эрх.')
            return redirect('main:permission_group_list')
    
    # Бүх эрхүүд
    permissions = Permission.objects.filter(
        content_type__app_label='main'
    ).select_related('content_type').order_by('content_type__model', 'codename')
    
    context = {
        'permissions': permissions,
        'group': group,
    }
    return render(request, 'main/permission_group_form.html', context)


@login_required
def permission_group_delete(request, group_id):
    """Эрхийн бүлэг устгах"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч энэ хуудсанд хандах боломжтой.')
        return redirect('main:dashboard')
    
    group = get_object_or_404(Group, id=group_id)
    
    # Хэрэглэгч байгаа эсэхийг шалгах
    if group.user_set.exists():
        messages.error(request, f'"{group.name}" бүлэгт {group.user_set.count()} хэрэглэгч байгаа тул устгах боломжгүй.')
        return redirect('main:permission_group_list')
    
    if request.method == 'POST':
        name = group.name
        group.delete()
        messages.success(request, f'✓ "{name}" бүлэг устгагдлаа.')
        return redirect('main:permission_group_list')
    
    # GET request - батлах хуудас харуулах (эсвэл шууд POST хүсвэл)
    group.delete()
    messages.success(request, f'✓ "{group.name}" бүлэг устгагдлаа.')
    return redirect('main:permission_group_list')


@login_required
def user_groups_edit(request, user_id):
    """Хэрэглэгчид эрхийн бүлэг зааж өгөх"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Зөвхөн админ хэрэглэгч энэ хуудсанд хандах боломжтой.')
        return redirect('main:dashboard')
    
    edit_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        group_ids = request.POST.getlist('groups')
        
        # Бүлгүүд шинэчлэх
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids)
            edit_user.groups.set(groups)
            messages.success(request, f'✓ {edit_user.profile.mongolian_name or edit_user.username} хэрэглэгчийн эрхийн бүлэг шинэчлэгдлээ.')
        else:
            edit_user.groups.clear()
            messages.success(request, f'✓ {edit_user.profile.mongolian_name or edit_user.username} хэрэглэгчийн бүх бүлэг хасагдлаа.')
        
        return redirect('main:student_list')
    
    all_groups = Group.objects.all().prefetch_related('permissions')
    
    context = {
        'edit_user': edit_user,
        'all_groups': all_groups,
    }
    return render(request, 'main/user_groups_edit.html', context)
