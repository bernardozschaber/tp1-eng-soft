from django import forms

from apps.catalog.models import Sector, TaxSettings, Unit


class TaxSettingsForm(forms.ModelForm):
    class Meta:
        model = TaxSettings
        fields = ["inss_rate", "iss_rate", "ir_rate"]
        widgets = {name: forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}) for name in fields}

    def clean(self):
        cleaned = super().clean()
        total = sum(cleaned.get(name) or 0 for name in ("inss_rate", "iss_rate", "ir_rate"))
        if total >= 100:
            raise forms.ValidationError("A soma das alíquotas precisa ser menor que 100%.")
        return cleaned


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name", "paying_company", "is_default"]


class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ["name", "is_default"]
