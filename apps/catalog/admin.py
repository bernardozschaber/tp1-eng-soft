from django.contrib import admin

from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit

admin.site.register(PayingCompany)
admin.site.register(Unit)
admin.site.register(Sector)
admin.site.register(TaxSettings)
