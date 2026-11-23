"""`manage.py roster` e a leitura das planilhas do setor que ele usa.

As planilhas reais (controle de RPAs e agendamento) têm dados pessoais e não
entram no repositório. Os testes montam em disco planilhas com o mesmo layout —
o cabeçalho repetido a cada quinzena, as linhas de TOTAL, a ficha com o
cabeçalho na linha 2 — e nomes, CPFs e contas inventados.
"""
from datetime import date, datetime

from django.test import SimpleTestCase

from apps.applicators.spreadsheets import (
    _as_date,
    _split_bank_details,
    _text,
)

# --- leitura das planilhas ---------------------------------------------------


class CellHelpersTests(SimpleTestCase):
    def test_text_of_empty_cell_is_blank(self):
        self.assertEqual(_text(None), "")

    def test_text_of_datetime_is_brazilian_date(self):
        self.assertEqual(_text(datetime(2026, 9, 15)), "15/09/2026")

    def test_text_of_whole_float_drops_the_decimal(self):
        # O Excel guarda telefone e conta como número: 31999990000.0.
        self.assertEqual(_text(31999990000.0), "31999990000")
        self.assertEqual(_text(10.5), "10.5")

    def test_text_collapses_whitespace(self):
        self.assertEqual(_text("  Ana   Souza \n"), "Ana Souza")

    def test_as_date_accepts_datetime_date_and_both_text_formats(self):
        self.assertEqual(_as_date(datetime(2001, 3, 14, 10, 0)), date(2001, 3, 14))
        self.assertEqual(_as_date(date(2001, 3, 14)), date(2001, 3, 14))
        self.assertEqual(_as_date("14/03/2001"), date(2001, 3, 14))
        self.assertEqual(_as_date("2001-03-14"), date(2001, 3, 14))

    def test_as_date_gives_up_on_anything_else(self):
        self.assertIsNone(_as_date("março de 2001"))
        self.assertIsNone(_as_date(None))

    def test_split_bank_details(self):
        self.assertEqual(_split_bank_details("3824 / 01090861-6"), ("3824", "01090861-6"))
        self.assertEqual(_split_bank_details(" 01090861-6 "), ("", "01090861-6"))