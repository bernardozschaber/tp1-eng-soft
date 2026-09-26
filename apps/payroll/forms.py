"""Forms for manual service entries."""
from django import forms

from apps.applicators.models import Applicator
from apps.payroll.models import ServiceEntry


class ServiceEntryForm(forms.ModelForm):
    applicator = forms.ModelChoiceField(
        queryset=Applicator.objects.filter(is_active=True), label="Aplicador", empty_label="Selecione…"
    )
    # Blank means "compute from the activity date" (see ServiceEntry.apply_calculations).
    payment_date = forms.DateField(label="Data de pagamento", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = ServiceEntry
        fields = [
            "applicator", "role", "activity_date", "event_name", "segment", "shift",
            "sector", "unit", "net_amount", "payment_date", "notes",
        ]
        widgets = {
            "activity_date": forms.DateInput(attrs={"type": "date"}),
            "net_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "placeholder": "0,00"}),
            "event_name": forms.TextInput(attrs={"placeholder": "Ex.: Simulado ENEM II"}),
            "segment": forms.TextInput(attrs={"placeholder": "Ex.: 3ª Série"}),
            "notes": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def clean_net_amount(self):
        amount = self.cleaned_data["net_amount"]
        if amount <= 0:
            raise forms.ValidationError("Informe um valor líquido maior que zero.")
        return amount
