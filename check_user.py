from django.contrib.auth.models import User, Group

try:
    user = User.objects.get(email='bayasaa68@gmail.com')
    print(f'✓ Хэрэглэгч олдлоо:')
    print(f'  Username: {user.username}')
    print(f'  Email: {user.email}')
    print(f'  is_staff: {user.is_staff}')
    print(f'  is_superuser: {user.is_superuser}')
    print(f'  is_active: {user.is_active}')
    print(f'  Бүлгүүд: {[g.name for g in user.groups.all()]}')
    
    # Эрх шалгах
    can_edit = user.is_staff and (user.is_superuser or user.groups.filter(name='Content Editor').exists())
    print(f'\n{"✓" if can_edit else "✗"} Агуулга засах эрх: {can_edit}')
    
    # Хэрэв Staff status байхгүй бол засах
    if not user.is_staff:
        print(f'\n⚠ Staff status байхгүй байна. Засаж байна...')
        user.is_staff = True
        user.save()
        print(f'✓ Staff status олгосон')
    
    # Хэрэв Content Editor группд харьяалагдаагүй бол нэмэх
    group = Group.objects.get(name='Content Editor')
    if not user.groups.filter(name='Content Editor').exists():
        print(f'\n⚠ Content Editor бүлэгт байхгүй байна. Нэмж байна...')
        user.groups.add(group)
        print(f'✓ Content Editor бүлэгт нэмлээ')
    
    print(f'\n✓ Бүх тохиргоо хийгдлээ!')
    print(f'  {user.username} одоо агуулга засах эрхтэй.')
    
except User.DoesNotExist:
    print(f'✗ {email} email-тэй хэрэглэгч олдсонгүй')
except Group.DoesNotExist:
    print(f'✗ Content Editor бүлэг байхгүй байна')
    print(f'  python manage.py setup_content_editor командыг ажиллуулна уу')
except Exception as e:
    print(f'✗ Алдаа: {e}')
