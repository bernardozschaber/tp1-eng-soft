from django.contrib import admin

from apps.applicators.models import Applicator


@admin.register(Applicator)
class ApplicatorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "cpf", "needs_review", "is_active")
    search_fields = ("full_name", "cpf")
