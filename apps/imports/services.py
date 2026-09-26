"""
Import workflow:

  1. `stage_uploads`    parse every uploaded workbook and keep a JSON-friendly
                        preview in the session (no database writes yet);
  2. `enrich_preview`   attach applicator matches, duplicate flags and the
                        computed gross amount so the preview page can show them;
  3. `confirm_import`   read the (possibly edited) preview back from the POST
                        payload and persist entries, creating missing applicators.
"""
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.applicators.models import Applicator
from apps.applicators.names import normalize_name, split_suffix, to_display_name
from apps.catalog.models import Sector, TaxSettings, Unit
from apps.imports.parser import ParsedWorkbook, parse_workbook
from apps.payroll.calculator import TaxRates, compute_breakdown
from apps.payroll.models import ImportBatch, ServiceEntry, ServiceRole

SESSION_KEY = "import_preview"


# --- staging ---------------------------------------------------------------

def _workbook_to_dict(workbook: ParsedWorkbook) -> dict:
    data = asdict(workbook)
    data["row_count"] = workbook.row_count
    for sheet in data["sheets"]:
        sheet["activity_date"] = sheet["activity_date"].isoformat() if sheet["activity_date"] else ""
        for row in sheet["rows"]:
            row["net_amount"] = str(row["net_amount"])
    return data


def stage_uploads(session, uploaded_files) -> list[dict]:
    """Parses the files and stores the preview in the session. Returns per-file errors."""
    workbooks, errors = [], []
    for uploaded in uploaded_files:
        try:
            workbooks.append(_workbook_to_dict(parse_workbook(uploaded.name, uploaded.read())))
        except Exception as error:  # noqa: BLE001 - surface any parser failure to the user
            errors.append({"file_name": uploaded.name, "message": str(error)})
    session[SESSION_KEY] = workbooks
    return errors


def load_preview(session) -> list[dict]:
    return session.get(SESSION_KEY, [])


def clear_preview(session) -> None:
    session.pop(SESSION_KEY, None)


# --- enrichment ------------------------------------------------------------

def _current_rates() -> TaxRates:
    tax = TaxSettings.current()
    return TaxRates.from_percentages(tax.inss_rate, tax.iss_rate, tax.ir_rate)


def _is_duplicate(applicator: Applicator | None, activity_date: str, event_name: str, net_amount: Decimal) -> bool:
    if applicator is None or not activity_date:
        return False
    return ServiceEntry.objects.filter(
        applicator=applicator, activity_date=activity_date, event_name__iexact=event_name.strip(), net_amount=net_amount
    ).exists()


def enrich_preview(workbooks: list[dict]) -> list[dict]:
    """Adds display name, match status, duplicate flag and gross amount to each row."""
    rates = _current_rates()
    for file_index, workbook in enumerate(workbooks):
        for sheet_index, sheet in enumerate(workbook["sheets"]):
            # Field-name prefixes shared with confirm_import (the template just echoes them).
            sheet["prefix"] = f"sheet-{file_index}-{sheet_index}"
            for row_index, row in enumerate(sheet["rows"]):
                row["prefix"] = f"{sheet['prefix']}-row-{row_index}"
                base_name, suffix = split_suffix(row["name"])
                applicator = Applicator.find_by_name(base_name)
                net_amount = Decimal(row["net_amount"])
                row["display_name"] = applicator.full_name if applicator else to_display_name(base_name)
                row["suffix"] = suffix
                row["is_known"] = applicator is not None
                row["is_duplicate"] = _is_duplicate(applicator, sheet["activity_date"], sheet["event_name"], net_amount)
                row["gross_amount"] = str(compute_breakdown(net_amount, rates).gross_amount)
    return workbooks


# --- confirmation ----------------------------------------------------------

def _get_or_create_applicator(raw_name: str, suffix: str) -> tuple[Applicator, bool]:
    applicator = Applicator.find_by_name(raw_name)
    if applicator:
        return applicator, False
    applicator = Applicator.objects.create(
        full_name=to_display_name(raw_name),
        needs_review=True,
        notes=f"Criado automaticamente pela importação. Sufixo na lista: {suffix}" if suffix else "Criado automaticamente pela importação.",
    )
    return applicator, True


def _read_sheet_fields(payload, prefix: str) -> dict:
    return {
        "event_name": payload.get(f"{prefix}-event_name", "").strip(),
        "activity_date": payload.get(f"{prefix}-activity_date", ""),
        "unit_id": payload.get(f"{prefix}-unit"),
        "sector_id": payload.get(f"{prefix}-sector"),
        "shift": payload.get(f"{prefix}-shift", ""),
    }


@transaction.atomic
def confirm_import(payload, workbooks: list[dict], user) -> dict:
    """Persists the selected rows. Returns counters for the success message."""
    created_entries = created_applicators = skipped_rows = 0
    for file_index, workbook in enumerate(workbooks):
        batch = None
        for sheet_index, sheet in enumerate(workbook["sheets"]):
            prefix = f"sheet-{file_index}-{sheet_index}"
            if payload.get(f"{prefix}-include") != "on":
                continue
            fields = _read_sheet_fields(payload, prefix)
            if not fields["event_name"] or not fields["activity_date"]:
                raise ValueError(f"Aba '{sheet['sheet_name']}' de {workbook['file_name']}: informe nome da atividade e data.")
            unit = Unit.objects.get(pk=fields["unit_id"])
            sector = Sector.objects.get(pk=fields["sector_id"])
            activity_date = date.fromisoformat(fields["activity_date"])
            for row_index, row in enumerate(sheet["rows"]):
                row_prefix = f"{prefix}-row-{row_index}"
                if payload.get(f"{row_prefix}-include") != "on":
                    skipped_rows += 1
                    continue
                net_amount = Decimal(payload.get(f"{row_prefix}-net_amount", row["net_amount"]).replace(",", "."))
                role = payload.get(f"{row_prefix}-role", row["role"])
                base_name, suffix = split_suffix(row["name"])
                applicator, was_created = _get_or_create_applicator(base_name, suffix)
                created_applicators += int(was_created)
                if batch is None:
                    batch = ImportBatch.objects.create(file_name=workbook["file_name"], imported_by=user)
                ServiceEntry.objects.create(
                    applicator=applicator,
                    role=role if role in ServiceRole.values else ServiceRole.APPLICATOR,
                    activity_date=activity_date,
                    event_name=fields["event_name"],
                    shift=fields["shift"],
                    sector=sector,
                    unit=unit,
                    net_amount=net_amount,
                    notes=suffix,
                    import_batch=batch,
                    created_by=user,
                )
                created_entries += 1
    return {"entries": created_entries, "applicators": created_applicators, "skipped": skipped_rows}


# --- non-interactive import (used by `manage.py seed --demo`) --------------

def import_with_defaults(file_name: str, content: bytes, user=None) -> dict:
    """Imports every sheet of a workbook using the default unit and sector, without preview."""
    workbook = parse_workbook(file_name, content)
    unit = Unit.objects.get(is_default=True)
    sector = Sector.objects.get(is_default=True)
    created_entries = created_applicators = 0
    with transaction.atomic():
        batch = ImportBatch.objects.create(file_name=file_name, imported_by=user)
        for sheet in workbook.sheets:
            for row in sheet.rows:
                base_name, suffix = split_suffix(row.name)
                applicator, was_created = _get_or_create_applicator(base_name, suffix)
                created_applicators += int(was_created)
                ServiceEntry.objects.create(
                    applicator=applicator, role=row.role, activity_date=sheet.activity_date, event_name=sheet.event_name,
                    shift=sheet.shift, sector=sector, unit=unit, net_amount=row.net_amount, notes=suffix,
                    import_batch=batch, created_by=user,
                )
                created_entries += 1
    return {"entries": created_entries, "applicators": created_applicators}
