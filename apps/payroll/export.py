"""Excel export mirroring the two legacy sheets (listing + summary)."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from apps.payroll.summary import SummaryGroup

HEADER_FILL = PatternFill("solid", fgColor="F0F0F0")
HEADER_FONT = Font(bold=True)
MONEY_FORMAT = '"R$"#,##0.00'
DATE_FORMAT = "DD/MM/YYYY"

LISTING_HEADERS = [
    "NOME APLICADOR", "VALOR LÍQUIDO", "APLICADOR / ORIENTADOR", "DATA DA PROVA / ATIVIDADE",
    "PROVA/EVENTO", "SEGMENTO", "SETOR SOLICITANTE", "UNIDADE ESCOLAR DA APLICAÇÃO",
    "DATA PAGAMENTO", "EMPRESA PAGADORA", "VALOR BRUTO (RPA)", "INSS", "ISS", "IR", "OBSERVAÇÕES",
]
SUMMARY_HEADERS = [
    "DATA DE PAGAMENTO", "APLICADOR", "EMPRESA", "VALOR BRUTO (RPA)", "INSS", "ISS", "IR",
    "VALOR LÍQUIDO A PAGAR", "CONSISTÊNCIA",
]


def _write_header(sheet, headers: list[str]) -> None:
    sheet.append(headers)
    for cell in sheet[sheet.max_row]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")


def _autosize(sheet) -> None:
    for column_cells in sheet.columns:
        width = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = min(max(12, width + 2), 45)


def _format_row(sheet, money_columns: list[int], date_columns: list[int]) -> None:
    row = sheet[sheet.max_row]
    for index in money_columns:
        row[index].number_format = MONEY_FORMAT
    for index in date_columns:
        row[index].number_format = DATE_FORMAT


def build_workbook(entries, groups: list[SummaryGroup]) -> bytes:
    workbook = Workbook()
    listing = workbook.active
    listing.title = "Listagem Serviços"
    _write_header(listing, LISTING_HEADERS)
    for entry in entries:
        listing.append([
            entry.applicator.full_name, entry.net_amount, entry.get_role_display().upper(), entry.activity_date,
            entry.event_name, entry.segment, entry.sector.name, entry.unit.name, entry.payment_date,
            entry.paying_company.name, entry.gross_amount, entry.inss_amount, entry.iss_amount, entry.ir_amount,
            entry.notes,
        ])
        _format_row(listing, money_columns=[1, 10, 11, 12, 13], date_columns=[3, 8])
    _autosize(listing)

    summary = workbook.create_sheet("Resumo por Aplicador")
    for group in groups:
        summary.append([f"RESUMO POR APLICADOR - PAGAMENTO {group.payment_date:%d/%m/%Y}"])
        summary[summary.max_row][0].font = HEADER_FONT
        _write_header(summary, SUMMARY_HEADERS)
        for row in group.rows:
            summary.append([
                row.payment_date, row.applicator_name, row.company_name, row.gross, row.inss, row.iss, row.ir,
                row.net_payable, "OK" if row.is_consistent else "ver",
            ])
            _format_row(summary, money_columns=[3, 4, 5, 6, 7], date_columns=[0])
        summary.append(["Total", "", "", group.total("gross"), group.total("inss"), group.total("iss"), group.total("ir"), group.total("net_payable"), ""])
        _format_row(summary, money_columns=[3, 4, 5, 6, 7], date_columns=[])
        for cell in summary[summary.max_row]:
            cell.font = HEADER_FONT
        summary.append([])
    _autosize(summary)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
