from django.contrib import admin
from django.apps import apps
from unfold.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

admin.site.site_header = "Senior Care Admin Panel"
admin.site.site_title = "Senior Care Admin"
admin.site.index_title = "Welcome to Senior Care Administration"

from .models import User

class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Fields', {'fields': ('user_type', 'phone_number', 'address', 'city', 'state', 'zip_code', 'date_of_birth', 'emergency_contact_name', 'emergency_contact_phone', 'profile_picture', 'is_active_user')}),
    )

app_models = apps.get_app_config('senior_care').get_models()

for model in app_models:
    try:
        if model == User:
            admin.site.register(User, CustomUserAdmin)
        else:
            class CustomAdmin(ModelAdmin):
                pass
            admin.site.register(model, CustomAdmin)
    except admin.sites.AlreadyRegistered:
        pass