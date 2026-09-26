from django import forms

from apps.applicators.models import Applicator
from apps.applicators.names import normalize_name


class ApplicatorForm(forms.ModelForm):
    class Meta:
        model = Applicator
        fields = [
            "full_name", "cpf", "email", "phone", "course", "institution",
            "bank_name", "bank_branch", "bank_account", "pix_key", "notes", "needs_review", "is_active",
        ]
        widgets = {
            "cpf": forms.TextInput(attrs={"placeholder": "000.000.000-00"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_full_name(self):
        """Collapses spaces and refuses a name that already exists (ignoring accents/case)."""
        name = " ".join(self.cleaned_data["full_name"].split())
        clash = Applicator.objects.exclude(pk=self.instance.pk).filter(normalized_name=normalize_name(name)).first()
        if clash:
            raise forms.ValidationError(f"Já existe um aplicador com este nome: {clash.full_name}.")
        return name
