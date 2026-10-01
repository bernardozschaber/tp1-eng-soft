from django.urls import path

from apps.imports import views

app_name = "imports"

urlpatterns = [
    path("", views.upload, name="upload"),
    path("previa/", views.preview, name="preview"),
    path("confirmar/", views.confirm, name="confirm"),
    path("descartar/", views.discard, name="discard"),
    path("lote/<int:pk>/", views.batch_preview, name="batch_preview"),
    path("lote/<int:pk>/arquivo/", views.batch_download, name="batch_download"),
    path("lote/<int:pk>/excluir/", views.batch_delete, name="batch_delete"),
    path("lotes/excluir/", views.batch_bulk_delete, name="batch_bulk_delete"),
]
