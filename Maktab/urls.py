from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.views import custom_404, custom_403, custom_500

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.urls')),
]

# Media fayllarini debug rejimida serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# Custom xato sahifalari
handler404 = custom_404
handler403 = custom_403
handler500 = custom_500
