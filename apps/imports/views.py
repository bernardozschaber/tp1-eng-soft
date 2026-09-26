"""Upload -> preview -> confirm flow for payment lists."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Sector, Unit
from apps.imports.services import clear_preview, confirm_import, enrich_preview, load_preview, stage_uploads
from apps.payroll.models import ImportBatch, Shift

ALLOWED_EXTENSIONS = (".xlsx", ".xlsm")


@login_required
def upload(request):
    if request.method == "POST":
        files = [file for file in request.FILES.getlist("files") if file.name.lower().endswith(ALLOWED_EXTENSIONS)]
        if not files:
            messages.error(request, "Selecione ao menos um arquivo .xlsx ou .xlsm.")
            return redirect("imports:upload")
        for error in stage_uploads(request.session, files):
            messages.error(request, f"{error['file_name']}: {error['message']}")
        return redirect("imports:preview")
    recent_batches = ImportBatch.objects.select_related("imported_by").prefetch_related("entries")[:10]
    return render(request, "imports/upload.html", {"recent_batches": recent_batches})


@login_required
def preview(request):
    workbooks = load_preview(request.session)
    if not workbooks:
        return redirect("imports:upload")
    context = {
        "workbooks": enrich_preview(workbooks),
        "units": Unit.objects.all(),
        "sectors": Sector.objects.all(),
        "shifts": Shift.choices,
        "default_unit": Unit.objects.filter(is_default=True).first(),
        "default_sector": Sector.objects.filter(is_default=True).first(),
        "total_rows": sum(workbook["row_count"] for workbook in workbooks),
    }
    return render(request, "imports/preview.html", context)


@login_required
@require_POST
def confirm(request):
    workbooks = load_preview(request.session)
    if not workbooks:
        return redirect("imports:upload")
    try:
        result = confirm_import(request.POST, workbooks, request.user)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("imports:preview")
    clear_preview(request.session)
    summary = f"{result['entries']} lançamento(s) importado(s)"
    if result["applicators"]:
        summary += f", {result['applicators']} aplicador(es) criado(s) para revisão"
    if result["skipped"]:
        summary += f", {result['skipped']} linha(s) ignorada(s)"
    messages.success(request, summary + ".")
    return redirect("payroll:entry_list")


@login_required
@require_POST
def discard(request):
    clear_preview(request.session)
    return redirect("imports:upload")
