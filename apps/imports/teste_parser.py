"""Item 3 do roteiro de TESTES.md: o parser, porta de entrada de todo dado.

Os dois layouts ("Relatório de Atividade" e exportação de formulário), as datas
por extenso e curtas, o valor com "R$" e vírgula, e a regra de que o que está
oculto na planilha — aba, linha ou coluna — não é lido. As planilhas são
montadas em memória, com nomes inventados.
"""
from datetime import date, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from apps.imports.parser import (
    format_cpf,
    parse_amount,
    parse_date,
    parse_role,
    parse_sheet,
    parse_shift,
)


def activity_rows(people, *, event="Simulado ENEM", when="15 de Setembro de 2026", shift="Horário: Manhã",
                  tail=()) -> list[tuple]:
    """As linhas de uma aba "Relatório de Atividade", como o openpyxl as devolve.

    Cada pessoa é (nome, valor) ou (nome, valor, "orientador").
    """
    blank = (None,) * 9
    rows = [
        (None, None, None, "Relatório de Atividade", None, None, None, None, None),
        (None, None, None, "Segmento da Atividade:", None, event, "Data:", when, None),
        (None, None, None, "Empresa:", None, "Matriz", None, None, shift),
        (None, None, None, "Nome", None, "Aplicador", "Orientador (a)", "Valor", None),
    ]
    for person in people:
        name, amount, *role = person
        advisor = 1 if role else None
        rows.append((None, None, None, name, None, None if advisor else 1, advisor, amount, None))
    return rows + [blank, *tail]


# --- células ---------------------------------------------------------------


class ParseDateTests(SimpleTestCase):
    def test_cell_types(self):
        self.assertEqual(parse_date(datetime(2026, 9, 15, 8, 0)), date(2026, 9, 15))
        self.assertEqual(parse_date(date(2026, 9, 15)), date(2026, 9, 15))

    def test_long_portuguese_date_with_and_without_accent(self):
        self.assertEqual(parse_date("Segunda, 15 de Setembro de 2026"), date(2026, 9, 15))
        self.assertEqual(parse_date("2 de março de 2026"), date(2026, 3, 2))
        self.assertEqual(parse_date("2 de MARCO de 2026"), date(2026, 3, 2))

    def test_short_date(self):
        self.assertEqual(parse_date("15/09/2026"), date(2026, 9, 15))

    def test_unknown_month_falls_back_to_short_date_or_none(self):
        self.assertIsNone(parse_date("15 de Setembroo de 2026"))
        self.assertIsNone(parse_date(None))
        self.assertIsNone(parse_date("amanhã"))


class ParseCellTests(SimpleTestCase):
    def test_shift_keywords(self):
        self.assertEqual(parse_shift("Horário: Manhã"), "MANHA")
        self.assertEqual(parse_shift("HORÁRIO: TARDE"), "TARDE")
        self.assertEqual(parse_shift("noite"), "NOITE")
        self.assertEqual(parse_shift(None), "")

    def test_amount_from_numbers_and_brazilian_text(self):
        self.assertEqual(parse_amount(102), Decimal("102"))
        self.assertEqual(parse_amount(102.5), Decimal("102.5"))
        self.assertEqual(parse_amount("R$ 1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_amount("115,00"), Decimal("115.00"))

    def test_amount_rejects_formulas_blanks_zero_and_text(self):
        for value in (None, "=SUM(H5:H20)", 0, -10, "", "a combinar"):
            with self.subTest(value=value):
                self.assertIsNone(parse_amount(value))

    def test_cpf_is_normalized_only_with_eleven_digits(self):
        self.assertEqual(format_cpf("52998224725"), "529.982.247-25")
        self.assertEqual(format_cpf(" 529.982.247-25 "), "529.982.247-25")
        self.assertEqual(format_cpf("1234"), "1234")
        self.assertEqual(format_cpf(None), "")

    def test_role_by_keyword_defaults_to_applicator(self):
        self.assertEqual(parse_role("Orientador(a)"), "ORIENTADOR")
        self.assertEqual(parse_role("VOLANTE"), "VOLANTE")
        self.assertEqual(parse_role("Aplicador de prova"), "APLICADOR")
        self.assertEqual(parse_role(""), "APLICADOR")


# --- layout "Relatório de Atividade" ------------------------------------------


class ParseActivitySheetTests(SimpleTestCase):
    def test_reads_metadata_and_people(self):
        sheet = parse_sheet("MANHÃ", activity_rows([("ANA SOUZA", 115, "orientador"), ("BRUNO LIMA", 102)]))

        self.assertEqual(
            (sheet.event_name, sheet.activity_date, sheet.shift, sheet.company_hint),
            ("Simulado ENEM", date(2026, 9, 15), "MANHA", "Matriz"),
        )
        self.assertEqual(
            [(row.name, row.role, row.net_amount, row.source_row) for row in sheet.rows],
            [("ANA SOUZA", "ORIENTADOR", Decimal("115"), 5), ("BRUNO LIMA", "APLICADOR", Decimal("102"), 6)],
        )
        self.assertEqual(sheet.warnings, [])
        self.assertFalse(sheet.needs_amount)

    def test_sheet_without_the_header_is_not_this_layout(self):
        self.assertIsNone(parse_sheet("Plan1", [("qualquer", "coisa")] * 10))

    def test_missing_event_and_date_become_warnings(self):
        sheet = parse_sheet("ABA", activity_rows([("ANA SOUZA", 102)], event=None, when="a definir"))

        self.assertIn("Nome da atividade não encontrado; informe manualmente.", sheet.warnings)
        self.assertIn("Data não reconhecida; informe manualmente.", sheet.warnings)

    def test_row_without_amount_is_warned_and_skipped(self):
        sheet = parse_sheet("ABA", activity_rows([("ANA SOUZA", None), ("BRUNO LIMA", 102)]))

        self.assertEqual([row.name for row in sheet.rows], ["BRUNO LIMA"])
        self.assertEqual(sheet.warnings, ["Linha 5: 'ANA SOUZA' sem valor válido, ignorada."])

    def test_short_names_are_skipped_silently(self):
        sheet = parse_sheet("ABA", activity_rows([("X", 102), ("BRUNO LIMA", 102)]))

        self.assertEqual([row.name for row in sheet.rows], ["BRUNO LIMA"])
        self.assertEqual(sheet.warnings, [])

    def test_reading_stops_at_the_totals_formula_and_the_signature(self):
        signature = (None, None, None, "ASSINATURA DO RESPONSÁVEL", None, None, None, None, None)
        after = (None, None, None, "DEPOIS DA ASSINATURA", None, 1, None, 102, None)
        total = (None, None, None, "=CONCAT(\"Total\")", None, None, None, "=SUM(H5:H5)", None)

        for tail in ((signature, after), (total, after)):
            with self.subTest(stop=tail[0][3]):
                sheet = parse_sheet("ABA", activity_rows([("ANA SOUZA", 102)], tail=tail))
                self.assertEqual([row.name for row in sheet.rows], ["ANA SOUZA"])