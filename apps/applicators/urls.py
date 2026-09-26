from django.urls import path

from apps.applicators import views

app_name = "applicators"

urlpatterns = [
    path("", views.applicator_list, name="list"),
    path("novo/", views.applicator_create, name="create"),
    path("<int:pk>/", views.applicator_detail, name="detail"),
    path("<int:pk>/editar/", views.applicator_update, name="update"),
]
