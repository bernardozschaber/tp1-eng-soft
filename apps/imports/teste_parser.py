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
    parse_shift,
)

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