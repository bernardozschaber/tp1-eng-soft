from django.contrib.auth import views as auth_views
from django.urls import path

from apps.core import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ajuda/", views.help_page, name="help"),
    path("perfil/", views.profile, name="profile"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
