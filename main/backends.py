"""
Custom authentication backend - утас эсвэл имэйлээр нэвтрэх
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class PhoneOrEmailBackend(ModelBackend):
    """
    Утас эсвэл имэйлээр нэвтрэх backend
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # Утас эсвэл имэйлээр хайх
            # 1. Эхлээд username-ээр шалгах (superuser, өмнөх систем)
            # 2. Дараа нь имэйлээр
            # 3. Утасны дугаараар (UserProfile-аас)
            
            user = None
            
            # Username эсвэл имэйлээр шалгах
            try:
                user = User.objects.get(
                    Q(username=username) | Q(email=username)
                )
            except User.DoesNotExist:
                # Утасны дугаараар хайх
                try:
                    from .models import UserProfile
                    # Утасны дугаар форматыг цэвэрлэх
                    phone = username.strip().replace(' ', '').replace('-', '')
                    profile = UserProfile.objects.select_related('user').get(
                        phone__icontains=phone[-8:]  # Сүүлийн 8 орон
                    )
                    user = profile.user
                except (UserProfile.DoesNotExist, UserProfile.MultipleObjectsReturned):
                    return None
            
            # Нууц үг шалгах
            if user and user.check_password(password):
                return user
                
        except Exception:
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
