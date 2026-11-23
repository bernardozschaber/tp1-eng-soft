from django.contrib import admin

from apps.core.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "role", "unit", "phone", "photo")
    list_select_related = ("user", "unit")
    search_fields = ("user__username", "user__first_name", "user__last_name", "role")
