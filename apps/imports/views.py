"""Upload -> preview -> confirm flow for payment lists."""
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from openpyxl import load_workbook

from apps.applicators.models import Applicator
from apps.catalog.models import Sector, Unit
from apps.imports.services import (
    all_questions,
    clear_preview,
    confirm_import,
    enrich_preview,
    load_preview,
    stage_uploads,
)
from apps.payroll.models import ImportBatch, ServiceEntry, Shift

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
    return render(request, "imports/upload.html", {"recent_batches": _recent_batches()})


def _recent_batches(limit: int = 10):
    """Os últimos lotes com o que a linha mostra: unidades, total e contagem.

    Os lançamentos já vêm no prefetch, então unidades, soma e contagem saem em
    memória — sem uma consulta por linha da tabela.
    """
    batches = list(
        ImportBatch.objects.select_related("imported_by__profile").prefetch_related(
            Prefetch("entries", queryset=ServiceEntry.objects.select_related("unit__paying_company"))
        )[:limit]
    )
    for batch in batches:
        entries = list(batch.entries.all())
        batch.entry_count = len(entries)
        batch.net_total = sum((entry.net_amount for entry in entries), Decimal("0"))
        codes = {}
        for entry in entries:
            codes.setdefault(entry.unit.short_name, None)
        batch.unit_codes = list(codes)
    return batches


@login_required
def preview(request):
    workbooks = load_preview(request.session)
    if not workbooks:
        return redirect("imports:upload")
    context = {
        "workbooks": enrich_preview(workbooks),
        "questions": all_questions(workbooks),
        # Para a terceira resposta ("associar a outro cadastro"): a busca é no
        # navegador, sobre esta lista, porque o card não recarrega a página.
        "applicators": Applicator.objects.filter(is_active=True).order_by("full_name"),
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
    if result["merged"]:
        summary += f", {result['merged']} lançamento(s) juntado(s) a um cadastro existente"
    if result["applicators"]:
        summary += f", {result['applicators']} cadastro(s) novo(s) criado(s) (primeiro pagamento)"
    if result["skipped"]:
        summary += f", {result['skipped']} linha(s) ignorada(s)"
    messages.success(request, summary + ".")
    if result["duplicates"]:
        # Avulso e em separado: não é detalhe do sucesso, é o operador
        # precisando saber que a lista trouxe serviço que já estava lançado.
        messages.warning(
            request,
            f"{result['duplicates']} linha(s) já estavam lançadas e não entraram de novo — "
            "mesma pessoa, mesma atividade, mesmo dia e mesmo turno. Confira se a data das "
            "abas da planilha está certa.",
        )
    return redirect("payroll:entry_list")


@login_required
@require_POST
def discard(request):
    clear_preview(request.session)
    return redirect("imports:upload")