"""
URL Configuration for Senior Care Backend
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API endpoints - THIS IS IMPORTANT!
    path('api/', include('senior_care.urls')),
    
    # Authentication
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = 'Senior Care Admin Panel'
admin.site.site_title = 'Senior Care Admin'
admin.site.index_title = 'Welcome to Senior Care Administration'