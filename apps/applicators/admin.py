from django.contrib import admin

from apps.applicators.forms import ApplicatorForm
from apps.applicators.models import Applicator


@admin.register(Applicator)
class ApplicatorAdmin(admin.ModelAdmin):
    # `normalized_name` não editável some da validação padrão do ModelForm, o
    # que deixaria "Gusmão" e "Gusmao" colidirem só na constraint do banco
    # (erro feio em vez de mensagem de formulário). O form do cadastro já
    # confere isso à mão.
    form = ApplicatorForm
    list_display = ("full_name", "cpf", "phone", "email", "registration_status", "is_active")
    search_fields = ("full_name", "cpf")
