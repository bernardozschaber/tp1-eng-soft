from django import forms

from apps.applicators.models import Applicator
from apps.applicators.names import normalize_name


class ApplicatorForm(forms.ModelForm):
    class Meta:
        model = Applicator
        fields = [
            "full_name", "cpf", "identity_document", "birth_date", "gender", "phone", "email",
            "neighborhood", "vse", "course", "course_period", "institution",
            "bank_name", "bank_branch", "bank_account", "account_type", "pix_type", "pix_key",
            "pis_nit", "referral", "photo", "notes", "registration_status", "is_active",
        ]
        widgets = {
            "cpf": forms.TextInput(attrs={"placeholder": "000.000.000-00"}),
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_full_name(self):
        """Collapses spaces and refuses a name that already exists (ignoring accents/case)."""
        name = " ".join(self.cleaned_data["full_name"].split())
        clash = Applicator.objects.exclude(pk=self.instance.pk).filter(normalized_name=normalize_name(name)).first()
        if clash:
            raise forms.ValidationError(f"Já existe um aplicador com este nome: {clash.full_name}.")
        return name
