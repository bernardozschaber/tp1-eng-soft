from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api import views

app_name = "api"

router = DefaultRouter()
router.register("aplicadores", views.ApplicatorViewSet, basename="applicator")
router.register("lancamentos", views.ServiceEntryViewSet, basename="entry")
router.register("unidades", views.UnitViewSet, basename="unit")
router.register("setores", views.SectorViewSet, basename="sector")
router.register("empresas", views.PayingCompanyViewSet, basename="company")

urlpatterns = [
    path("aliquotas/", views.tax_settings, name="tax-settings"),
    path("", include(router.urls)),
]
