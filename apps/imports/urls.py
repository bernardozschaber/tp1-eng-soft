from django.http import HttpResponse
from django.urls import path

urlpatterns: list = []
app_name = "imports"
urlpatterns = [path("", lambda r: HttpResponse("TODO"), name="upload")]