"""
Lê os dois formatos de lista que a operação usa.

**"Relatório de Atividade"** (Lourdes), com o valor dentro da planilha:

    row 1:  D="Segmento da Atividade:"  F=<event name>   G="Data:"  H=<date>
    row 2:  D="Empresa:"                F=<company>                 I="Horário: Manhã"
    row 3:  D="Nome"  F="Aplicador"  G="Orientador (a)"  H="Valor"
    row 4+: D=<full name>  F=1 (applicator) or G=1 (advisor)  H=<net amount>

**Exportação de formulário** (Cidade Jardim e Vale do Sereno), uma resposta por
linha, colunas localizadas pelo cabeçalho e não por posição:

    Id | Hora de início | Hora de conclusão | Email | Nome | Nome Completo | CPF | Data | Função

Esse formato **não traz valor**: a prova, o dia e o turno vêm do nome do arquivo
("Prova Regular 11-09 Tarde.xlsx") e o valor por pessoa é informado na
pré-visualização. As abas que não batem com nenhum dos dois são ignoradas e
reportadas. Em ambos os layouts, o que está oculto no arquivo — aba, linha ou
coluna — não é lido (veja `parse_workbook`).
"""
import posixpath
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

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

# --- exportação de formulário (Cidade Jardim, Vale do Sereno) ---------------
FORMS_HEADER_SCAN_ROWS = 5
FORMS_NAME_HEADERS = ("nome completo",)
FORMS_ROLE_HEADERS = ("funcao", "função")
ROLE_BY_KEYWORD = {"aplicador": "APLICADOR", "orientador": "ORIENTADOR", "volante": "VOLANTE"}
# "Prova Regular 11-09 Tarde.xlsx" -> dia 11, mês 09 (ano opcional).
FILE_NAME_DATE = re.compile(r"(?<!\d)(\d{1,2})[-_./](\d{1,2})(?:[-_./](\d{2,4}))?(?!\d)")


@dataclass
class ParsedRow:
    name: str
    role: str  # "APLICADOR" | "ORIENTADOR" | "VOLANTE"
    net_amount: Decimal
    source_row: int
    cpf: str = ""


@dataclass
class ParsedSheet:
    sheet_name: str
    event_name: str = ""
    activity_date: date | None = None
    shift: str = ""
    company_hint: str = ""
    rows: list[ParsedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # "atividade" traz o valor na planilha; "forms" não traz e precisa do valor
    # por pessoa na pré-visualização.
    layout: str = "atividade"
    needs_amount: bool = False


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


# --- exportação de formulário ----------------------------------------------

def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")


def _header_key(value) -> str:
    return _strip_accents(str(value or "")).strip().lower()


def format_cpf(value) -> str:
    """Normaliza o CPF para XXX.XXX.XXX-XX; devolve o texto cru se não tiver 11 dígitos."""
    text = str(value or "").strip()
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return text[:14]


def parse_role(value) -> str:
    key = _header_key(value)
    for keyword, role in ROLE_BY_KEYWORD.items():
        if keyword in key:
            return role
    return "APLICADOR"


def parse_file_name_meta(file_name: str) -> tuple[str, date | None, str]:
    """Tira prova, dia e turno do nome do arquivo do formulário.

    "Prova Regular 11-09 Tarde.xlsx" -> ("Prova Regular", 11/09, "TARDE"). O ano
    raramente aparece no nome; quem completa é a coluna "Data" de cada resposta.
    """
    stem = file_name.rsplit(".", 1)[0]
    shift = parse_shift(stem)
    activity_date, leftover = None, stem
    match = FILE_NAME_DATE.search(stem)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = match.group(3)
        if year:
            year = int(year)
            year += 2000 if year < 100 else 0
        try:
            activity_date = date(year or date.today().year, month, day)
        except ValueError:
            activity_date = None
        leftover = stem[: match.start()] + " " + stem[match.end() :]
    for keyword in SHIFT_KEYWORDS:
        leftover = re.sub(keyword + r"[a-zçã]*", " ", leftover, flags=re.IGNORECASE)
    event_name = re.sub(r"[\s_-]+", " ", leftover).strip(" -_")
    return event_name, activity_date, shift


def _find_forms_header(rows: list[tuple]) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(rows[:FORMS_HEADER_SCAN_ROWS]):
        columns = {_header_key(value): position for position, value in enumerate(row) if value not in (None, "")}
        has_name = any(header in columns for header in FORMS_NAME_HEADERS)
        has_role = any(_header_key(header) in columns for header in FORMS_ROLE_HEADERS)
        if has_name and has_role:
            return index, columns
    return None


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