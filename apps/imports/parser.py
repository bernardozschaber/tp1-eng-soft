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


def parse_forms_sheet(sheet_name: str, rows: list[tuple], file_name: str) -> ParsedSheet | None:
    """Uma resposta de formulário por linha: nome completo, CPF e função."""
    found = _find_forms_header(rows)
    if found is None:
        return None
    header_index, columns = found
    name_column = next(columns[header] for header in FORMS_NAME_HEADERS if header in columns)
    role_column = next(columns[_header_key(header)] for header in FORMS_ROLE_HEADERS if _header_key(header) in columns)
    cpf_column = columns.get("cpf")
    date_column = columns.get("data")

    event_name, activity_date, shift = parse_file_name_meta(file_name)
    sheet = ParsedSheet(
        sheet_name=sheet_name, event_name=event_name, activity_date=activity_date, shift=shift,
        layout="forms", needs_amount=True,
    )
    if not event_name:
        sheet.warnings.append("Nome da prova não veio no nome do arquivo; informe manualmente.")
    if shift == "":
        sheet.warnings.append("Turno não veio no nome do arquivo; informe manualmente.")
    sheet.warnings.append("Lista de formulário: informe o valor por pessoa e confirme a unidade (CJ ou Vale do Sereno).")

    for offset, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        name = str(_cell(row, name_column) or "").strip()
        if len(name) < MIN_NAME_LENGTH:
            continue
        if date_column is not None and sheet.activity_date is None:
            sheet.activity_date = parse_date(_cell(row, date_column))
        row_date = parse_date(_cell(row, date_column)) if date_column is not None else None
        if row_date and sheet.activity_date and row_date.year != sheet.activity_date.year:
            # O nome do arquivo não traz o ano; a resposta traz.
            sheet.activity_date = sheet.activity_date.replace(year=row_date.year)
        sheet.rows.append(ParsedRow(
            name=name,
            role=parse_role(_cell(row, role_column)),
            net_amount=Decimal("0"),
            source_row=offset,
            cpf=format_cpf(_cell(row, cpf_column)) if cpf_column is not None else "",
        ))
    if sheet.activity_date is None:
        sheet.warnings.append("Data não reconhecida; informe manualmente.")
    return sheet


# --- o que está oculto não é lido ------------------------------------------
#
# A visibilidade de linha e coluna não existe no modo read_only do openpyxl, e
# abrir a planilha no modo completo não é opção: uma aba que declara o intervalo
# inteiro (1.048.576 linhas) faz o openpyxl materializar a grade toda — medimos
# 7 GB de RAM num arquivo de 4 MB. O .xlsx é um zip de XML, então essa
# informação é lida direto da parte da aba, em streaming, sem montar grade.

SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
XML_TRUE = {"1", "true", "True"}


def _sheet_parts(archive: ZipFile) -> dict[str, str]:
    """Nome da aba -> caminho do XML dela dentro do zip."""
    targets = {}
    with archive.open("xl/_rels/workbook.xml.rels") as handle:
        for relationship in ElementTree.parse(handle).getroot():
            targets[relationship.get("Id")] = relationship.get("Target") or ""
    parts = {}
    with archive.open("xl/workbook.xml") as handle:
        for sheet in ElementTree.parse(handle).getroot().iter(f"{SHEET_NS}sheet"):
            target = targets.get(sheet.get(f"{DOC_REL_NS}id"), "")
            if not target:
                continue
            path = target[1:] if target.startswith("/") else posixpath.join("xl", target)
            parts[sheet.get("name")] = posixpath.normpath(path)
    return parts


def _hidden_in_part(archive: ZipFile, part: str) -> tuple[set[int], set[int]]:
    """(linhas ocultas, base 1; colunas ocultas, base 0) da parte de uma aba.

    Pega também o que o Excel escondeu por filtro ou agrupamento: os dois casos
    gravam hidden="1" na própria linha.
    """
    rows, columns = set(), set()
    with archive.open(part) as handle:
        for _, element in ElementTree.iterparse(handle, ("end",)):
            if element.tag == f"{SHEET_NS}col":
                if element.get("hidden") in XML_TRUE:
                    columns.update(range(int(element.get("min", 1)) - 1, int(element.get("max", 0))))
                element.clear()
            elif element.tag == f"{SHEET_NS}row":
                if element.get("hidden") in XML_TRUE and element.get("r"):
                    rows.add(int(element.get("r")))
                element.clear()
    return rows, columns


def _hidden_cells(content: bytes) -> dict[str, tuple[set[int], set[int]]]:
    """O que está oculto em cada aba. Um arquivo ilegível devolve nada e a
    importação segue pelo caminho normal do openpyxl."""
    hidden = {}
    try:
        with ZipFile(BytesIO(content)) as archive:
            for title, part in _sheet_parts(archive).items():
                try:
                    hidden[title] = _hidden_in_part(archive, part)
                except (KeyError, ElementTree.ParseError):
                    continue
    except (BadZipFile, KeyError, ElementTree.ParseError):
        return {}
    return hidden


def _visible_rows(worksheet, hidden: tuple[set[int], set[int]]) -> tuple[list[tuple], int]:
    """As linhas da aba com o que está oculto apagado. Devolve também quantas linhas caíram.

    Linha oculta vira linha vazia em vez de sair da lista: as posições são o que
    dá o "Linha 37" dos avisos, e renumerar apontaria o operador para a linha
    errada do Excel. Coluna oculta vira célula vazia, pela mesma razão — o
    layout "Relatório de Atividade" lê D, F, G e H por posição fixa.
    """
    hidden_rows, hidden_columns = hidden
    if not hidden_rows and not hidden_columns:
        # Nada oculto: devolve as linhas como vieram, sem reconstruir tupla nenhuma.
        return list(worksheet.iter_rows(values_only=True)), 0
    rows, dropped = [], 0
    for number, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
        if number in hidden_rows:
            rows.append(())
            dropped += any(value not in (None, "") for value in row)
            continue
        rows.append(tuple(None if index in hidden_columns else value for index, value in enumerate(row)))
    return rows, dropped


def parse_workbook(file_name: str, content: bytes) -> ParsedWorkbook:
    """Lê o que a planilha mostra: abas, linhas e colunas ocultas ficam de fora.

    A operação monta a lista de cada dia copiando a do dia anterior e ocultando
    o que não vale mais. O conteúdo continua no arquivo, com nomes, valores e a
    data antiga na célula "Data:" — uma lista de agosto carrega abas de maio e
    junho escondidas, e uma aba pode esconder a linha de quem faltou. Importar
    isso lança pagamentos de quinzenas já fechadas, e quem confere no Excel não
    vê o que não está à vista. A regra é única e vale para os dois layouts: o
    que está oculto não existe para o parser. Abas ocultas são reportadas em
    `skipped_sheets` e linhas ocultas em `ParsedSheet.warnings`, para a
    pré-visualização mostrar o que foi deixado de fora.
    """
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
    hidden_cells = _hidden_cells(content)
    result = ParsedWorkbook(file_name=file_name)
    try:
        for worksheet in workbook.worksheets:
            if worksheet.sheet_state != "visible":
                result.skipped_sheets.append(f"{worksheet.title} (oculta na planilha)")
                continue
            rows, hidden_row_count = _visible_rows(worksheet, hidden_cells.get(worksheet.title, (set(), set())))
            parsed = parse_sheet(worksheet.title, rows) or parse_forms_sheet(worksheet.title, rows, file_name)
            if parsed is None:
                result.skipped_sheets.append(worksheet.title)
                continue
            if hidden_row_count:
                parsed.warnings.append(
                    f"{hidden_row_count} linha(s) oculta(s) na planilha, ignorada(s) na importação."
                )
            if parsed.rows:
                result.sheets.append(parsed)
            else:
                result.skipped_sheets.append(f"{worksheet.title} (sem aplicadores)")
    finally:
        workbook.close()
    return result
