from django.urls import path

from apps.payroll import views

app_name = "payroll"

urlpatterns = [
    path("", views.entry_list, name="entry_list"),
    path("novo/", views.entry_create, name="entry_create"),
    path("<int:pk>/editar/", views.entry_update, name="entry_update"),
    path("<int:pk>/excluir/", views.entry_delete, name="entry_delete"),
    path("resumo/", views.summary, name="summary"),
    path("exportar/", views.export_excel, name="export"),
]
