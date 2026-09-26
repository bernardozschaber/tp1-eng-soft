"""Settings page: tax rates plus unit / sector reference tables."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.forms import SectorForm, TaxSettingsForm, UnitForm
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.calculator import TaxRates, compute_breakdown

EXAMPLE_NET = Decimal("100")


def _example_breakdown(tax: TaxSettings):
    return compute_breakdown(EXAMPLE_NET, TaxRates.from_percentages(tax.inss_rate, tax.iss_rate, tax.ir_rate))


@login_required
def settings_page(request):
    tax = TaxSettings.current()
    tax_form = TaxSettingsForm(instance=tax)
    unit_form, sector_form = UnitForm(), SectorForm()
    if request.method == "POST":
        target = request.POST.get("form")
        if target == "tax":
            tax_form = TaxSettingsForm(request.POST, instance=tax)
            if tax_form.is_valid():
                tax_form.save()
                messages.success(request, "Alíquotas atualizadas. Novos lançamentos usarão os novos valores.")
                return redirect("catalog:settings")
        elif target == "unit":
            unit_form = UnitForm(request.POST)
            if unit_form.is_valid():
                unit_form.save()
                messages.success(request, "Unidade cadastrada.")
                return redirect("catalog:settings")
        elif target == "sector":
            sector_form = SectorForm(request.POST)
            if sector_form.is_valid():
                sector_form.save()
                messages.success(request, "Setor cadastrado.")
                return redirect("catalog:settings")
    context = {
        "tax": tax,
        "tax_form": tax_form,
        "unit_form": unit_form,
        "sector_form": sector_form,
        "example": _example_breakdown(tax),
        "units": Unit.objects.select_related("paying_company"),
        "sectors": Sector.objects.all(),
        "companies": PayingCompany.objects.all(),
    }
    return render(request, "catalog/settings.html", context)


@login_required
@require_POST
def set_default(request, kind: str, pk: int):
    """Marks one unit or sector as the import default (exactly one per kind)."""
    model = Unit if kind == "unit" else Sector
    target = get_object_or_404(model, pk=pk)
    model.objects.update(is_default=False)
    target.is_default = True
    target.save(update_fields=["is_default"])
    messages.success(request, f"{target} definido como padrão.")
    return redirect("catalog:settings")
