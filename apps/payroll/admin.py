from django.contrib import admin

from apps.payroll.models import ImportBatch, ServiceEntry


@admin.register(ServiceEntry)
class ServiceEntryAdmin(admin.ModelAdmin):
    list_display = ("applicator", "event_name", "activity_date", "unit", "net_amount", "gross_amount", "payment_date")
    list_filter = ("unit", "sector", "role")
    search_fields = ("applicator__full_name", "event_name")


admin.site.register(ImportBatch)
