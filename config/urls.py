"""Root URL configuration: mounts each app under its own prefix."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.api.urls")),
    path("", include("apps.core.urls")),
    path("aplicadores/", include("apps.applicators.urls")),
    path("lancamentos/", include("apps.payroll.urls")),
    path("importar/", include("apps.imports.urls")),
    path("configuracoes/", include("apps.catalog.urls")),
]
