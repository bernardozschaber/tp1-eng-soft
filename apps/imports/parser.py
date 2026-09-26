"""
Reads "Relatório de Atividade" workbooks (the payment-list template).

Every sheet that follows the template looks like this (0-based columns):

    row 1:  D="Segmento da Atividade:"  F=<event name>   G="Data:"  H=<date>
    row 2:  D="Empresa:"                F=<company>                 I="Horário: Manhã"
    row 3:  D="Nome"  F="Aplicador"  G="Orientador (a)"  H="Valor"
    row 4+: D=<full name>  F=1 (applicator) or G=1 (advisor)  H=<net amount>

Sheets that do not match the layout are skipped and reported as warnings.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import load_workbook

NAME_COLUMN, APPLICATOR_COLUMN, ADVISOR_COLUMN, VALUE_COLUMN = 3, 5, 6, 7
HEADER_SCAN_ROWS = 8
MIN_NAME_LENGTH = 3

MONTHS_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
LONG_DATE = re.compile(r"(\d{1,2})\s+de\s+([A-Za-zçÇ]+)\s+de\s+(\d{4})", re.IGNORECASE)
SHORT_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
SHIFT_KEYWORDS = {"manh": "MANHA", "tarde": "TARDE", "noite": "NOITE"}


@dataclass
class ParsedRow:
    name: str
    role: str  # "APLICADOR" | "ORIENTADOR"
    net_amount: Decimal
    source_row: int


@dataclass
class ParsedSheet:
    sheet_name: str
    event_name: str = ""
    activity_date: date | None = None
    shift: str = ""
    company_hint: str = ""
    rows: list[ParsedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ParsedWorkbook:
    file_name: str
    sheets: list[ParsedSheet] = field(default_factory=list)
    skipped_sheets: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return sum(len(sheet.rows) for sheet in self.sheets)


def parse_date(value) -> date | None:
    """Accepts datetime cells, "27 de Junho de 2026" or "27/06/2026"."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    match = LONG_DATE.search(text)
    if match:
        month = MONTHS_PT.get(match.group(2).lower())
        if month:
            return date(int(match.group(3)), month, int(match.group(1)))
    match = SHORT_DATE.search(text)
    if match:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    return None


def parse_shift(text) -> str:
    lowered = str(text or "").lower()
    for keyword, code in SHIFT_KEYWORDS.items():
        if keyword in lowered:
            return code
    return ""


def parse_amount(value) -> Decimal | None:
    if value is None or isinstance(value, str) and value.startswith("="):
        return None
    try:
        amount = Decimal(str(value).replace("R$", "").replace(".", "").replace(",", ".")) if isinstance(value, str) else Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return amount if amount > 0 else None


def _cell(row: tuple, index: int):
    return row[index] if index < len(row) else None


def _find_header_row(rows: list[tuple]) -> int | None:
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        if str(_cell(row, NAME_COLUMN) or "").strip().lower() == "nome" and "valor" in str(_cell(row, VALUE_COLUMN) or "").lower():
            return index
    return None


def _read_metadata(sheet: ParsedSheet, rows: list[tuple], header_index: int) -> None:
    for row in rows[:header_index]:
        for index, value in enumerate(row):
            label = str(value or "").strip().lower()
            if label.startswith("segmento da atividade"):
                sheet.event_name = str(_cell(row, index + 2) or "").strip()
            elif label == "data:":
                sheet.activity_date = parse_date(_cell(row, index + 1))
            elif label == "empresa:":
                sheet.company_hint = str(_cell(row, index + 2) or "").strip()
            elif label.startswith("hor"):
                sheet.shift = parse_shift(value)


def parse_sheet(sheet_name: str, rows: list[tuple]) -> ParsedSheet | None:
    header_index = _find_header_row(rows)
    if header_index is None:
        return None
    sheet = ParsedSheet(sheet_name=sheet_name)
    _read_metadata(sheet, rows, header_index)
    if not sheet.event_name:
        sheet.warnings.append("Nome da atividade não encontrado; informe manualmente.")
    if sheet.activity_date is None:
        sheet.warnings.append("Data não reconhecida; informe manualmente.")

    for offset, row in enumerate(rows[header_index + 1:], start=header_index + 2):
        name = str(_cell(row, NAME_COLUMN) or "").strip()
        if not name or name.startswith("=") or len(name) < MIN_NAME_LENGTH:
            if name.startswith("="):
                break  # reached the totals row
            continue
        if name.lower().startswith("assinatura"):
            break
        amount = parse_amount(_cell(row, VALUE_COLUMN))
        if amount is None:
            sheet.warnings.append(f"Linha {offset}: '{name}' sem valor válido, ignorada.")
            continue
        role = "ORIENTADOR" if _cell(row, ADVISOR_COLUMN) else "APLICADOR"
        sheet.rows.append(ParsedRow(name=name, role=role, net_amount=amount, source_row=offset))
    return sheet


def parse_workbook(file_name: str, content: bytes) -> ParsedWorkbook:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
    result = ParsedWorkbook(file_name=file_name)
    for worksheet in workbook.worksheets:
        rows = list(worksheet.iter_rows(values_only=True))
        parsed = parse_sheet(worksheet.title, rows)
        if parsed is None:
            result.skipped_sheets.append(worksheet.title)
        elif parsed.rows:
            result.sheets.append(parsed)
        else:
            result.skipped_sheets.append(f"{worksheet.title} (sem aplicadores)")
    return result
