"""
URL configuration for gotopa_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(
        r'^static/images/багшнар/(?P<path>.*)$',
        serve,
        {'document_root': settings.BASE_DIR / 'static' / 'images' / 'багшнар'},
    ),
    path('', include('main.urls')),
]


# Static файлыг WhiteNoise дунд програм хангамж (middleware) DEBUG-с үл хамааран
# өгдөг тул энд дахин зарлах шаардлагагүй. Харин media (хэрэглэгчийн
# байршуулсан файл)-ыг WhiteNoise хариуцдаггүй тул энд DEBUG-с үл хамааран
# өөрөө үйлчилнэ (жижиг дотоод серверт nginx зэрэг тусдаа reverse proxy
# байхгүй тул ингэж хийж байна).
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
