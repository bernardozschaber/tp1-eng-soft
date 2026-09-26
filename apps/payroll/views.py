"""Service entries: list, create, edit, delete, summary and Excel export."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.applicators.models import Applicator
from apps.catalog.models import Sector, Unit
from apps.payroll.export import build_workbook
from apps.payroll.filters import EntryFilters
from apps.payroll.forms import ServiceEntryForm
from apps.payroll.models import ServiceEntry
from apps.payroll.summary import build_summary, grand_totals

PAGE_SIZE = 50


def _filter_options() -> dict:
    return {
        "units": Unit.objects.select_related("paying_company"),
        "sectors": Sector.objects.all(),
        "applicators": Applicator.objects.filter(is_active=True),
        "payment_dates": ServiceEntry.objects.order_by("-payment_date").values_list("payment_date", flat=True).distinct(),
    }


@login_required
def entry_list(request):
    filters = EntryFilters.from_request(request.GET)
    queryset = filters.apply()
    totals = queryset.aggregate(net=Sum("net_amount"), gross=Sum("gross_amount"), inss=Sum("inss_amount"), iss=Sum("iss_amount"), ir=Sum("ir_amount"))
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    entries = list(page.object_list)
    if filters.inconsistent_only:
        entries = [entry for entry in entries if not entry.is_consistent]
    context = {"filters": filters, "page": page, "entries": entries, "totals": totals, **_filter_options()}
    return render(request, "payroll/entry_list.html", context)


@login_required
def entry_create(request):
    form = ServiceEntryForm(request.POST or None, initial={"activity_date": date.today()})
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.created_by = request.user
        entry.save()
        messages.success(request, f"Lançamento de {entry.applicator} gravado.")
        return redirect("payroll:entry_list")
    return render(request, "payroll/entry_form.html", {"form": form, "title": "Novo lançamento"})


@login_required
def entry_update(request, pk: int):
    entry = get_object_or_404(ServiceEntry, pk=pk)
    form = ServiceEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Lançamento atualizado.")
        return redirect("payroll:entry_list")
    return render(request, "payroll/entry_form.html", {"form": form, "entry": entry, "title": "Editar lançamento"})


@login_required
@require_POST
def entry_delete(request, pk: int):
    entry = get_object_or_404(ServiceEntry, pk=pk)
    entry.delete()
    messages.success(request, "Lançamento excluído.")
    return redirect(request.POST.get("next") or "payroll:entry_list")


@login_required
def summary(request):
    filters = EntryFilters.from_request(request.GET)
    groups = build_summary(filters.apply())
    if filters.inconsistent_only:
        for group in groups:
            group.rows = [row for row in group.rows if not row.is_consistent]
        groups = [group for group in groups if group.rows]
    context = {"filters": filters, "groups": groups, "totals": grand_totals(groups), **_filter_options()}
    return render(request, "payroll/summary.html", context)


@login_required
def export_excel(request):
    filters = EntryFilters.from_request(request.GET)
    entries = filters.apply().order_by("activity_date", "applicator__full_name")
    content = build_workbook(entries, build_summary(entries))
    response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="ProvaPay_{date.today():%Y-%m-%d}.xlsx"'
    return response
