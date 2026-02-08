from django.contrib.auth.models import User
from main.models import UserProfile

print("\n=== Бүх хэрэглэгчид ===")
for user in User.objects.all():
    if hasattr(user, 'profile'):
        print(f"{user.username}: {user.profile.role} ({user.profile.get_role_display()})")
        print(f"  - is_admin: {user.profile.is_admin}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
    else:
        print(f"{user.username}: NO PROFILE")
