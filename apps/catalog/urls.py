from django.urls import path

from apps.catalog import views

app_name = "catalog"

urlpatterns = [
    path("", views.settings_page, name="settings"),
    path("padrao/<str:kind>/<int:pk>/", views.set_default, name="set_default"),
]
