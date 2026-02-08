from django.contrib.auth.models import User, Group

# Хэрэглэгч олох
user = User.objects.get(email='bayasaa68@gmail.com')
print(f'Username: {user.username}')
print(f'is_staff (одоо): {user.is_staff}')

# Staff эрх олгох
user.is_staff = True
user.save()
print(f'is_staff (шинэ): {user.is_staff}')

# Content Editor group-д нэмэх
group, created = Group.objects.get_or_create(name='Content Editor')
user.groups.add(group)
print(f'Groups: {[g.name for g in user.groups.all()]}')

print('\n✓ Амжилттай! Хэрэглэгч одоо агуулга засах эрхтэй.')
