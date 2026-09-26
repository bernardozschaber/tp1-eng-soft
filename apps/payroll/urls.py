from django.http import HttpResponse
from django.urls import path

urlpatterns: list = []
app_name = "payroll"
stub = lambda request: HttpResponse("TODO")  # noqa: E731
urlpatterns = [
    path("", stub, name="entry_list"),
    path("novo/", stub, name="entry_create"),
    path("resumo/", stub, name="summary"),
]