from django.urls import path

from apps.imports import views

app_name = "imports"

urlpatterns = [
    path("", views.upload, name="upload"),
    path("previa/", views.preview, name="preview"),
    path("confirmar/", views.confirm, name="confirm"),
    path("descartar/", views.discard, name="discard"),
]
