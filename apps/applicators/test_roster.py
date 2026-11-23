"""`manage.py roster` e a leitura das planilhas do setor que ele usa.

As planilhas reais (controle de RPAs e agendamento) têm dados pessoais e não
entram no repositório. Os testes montam em disco planilhas com o mesmo layout —
o cabeçalho repetido a cada quinzena, as linhas de TOTAL, a ficha com o
cabeçalho na linha 2 — e nomes, CPFs e contas inventados.
"""
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

from django.test import SimpleTestCase
from openpyxl import Workbook

from apps.applicators.spreadsheets import (
    PAYMENTS_SHEET,
    PROFILE_COLUMNS,
    PROFILES_SHEET,
    _as_date,
    _split_bank_details,
    _text,
    read_payment_names,
    read_profiles,
)

PROFILE_HEADER = list(PROFILE_COLUMNS.values())


def profile_row(name, **overrides) -> list:
    """Uma linha da ficha na ordem de PROFILE_HEADER, com valores inventados."""
    values = {
        "nome": name,
        "phone": "31 99999-0000",
        "cpf": "123.456.789-09",
        "identity_document": "MG-12.345.678",
        "birth_date": datetime(2001, 3, 14),
        "gender": "Feminino",
        "neighborhood": "Savassi",
        "vse": "",
        "email": "pessoa@email.com",
        "course": "Medicina",
        "course_period": "Manhã",
        "institution": "UFMG",
        "bank_details": "3824 / 01090861-6",
        "bank_name": "Itaú",
        "account_type": "Corrente",
        "pix_type": "CPF",
        "pix_key": "123.456.789-09",
        "pis_nit": "123.45678.90-1",
        "referral": "Instagram",
    }
    values.update(overrides)
    return [values[key] for key in PROFILE_COLUMNS]


class SpreadsheetDir:
    """Mixin: uma pasta temporária para gravar as planilhas de cada teste."""

    def make_dir(self) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        return directory

    def payments_workbook(self, blocks, *, sheet=PAYMENTS_SHEET, header="APLICADOR") -> str:
        """Uma aba de RPAs: cada bloco tem cabeçalho, nomes e linha de TOTAL."""
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet
        worksheet.append(["CONTROLE DE RPAS"])
        for block in blocks:
            worksheet.append([])
            worksheet.append(["DATA", header, "VALOR"])
            for name in block:
                worksheet.append(["15/09/2026", name, 102])
            worksheet.append(["", "TOTAL", 102 * len(block)])
        path = self.make_dir() / "RPAS.xlsx"
        workbook.save(path)
        return str(path)

    def profiles_workbook(self, rows, *, header=None, sheet=PROFILES_SHEET) -> str:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet
        worksheet.append(["Cadastro de aplicadores"])
        worksheet.append(header if header is not None else PROFILE_HEADER)
        for row in rows:
            worksheet.append(row)
        path = self.make_dir() / "Agendamento.xlsx"
        workbook.save(path)
        return str(path)


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


class ReadPaymentNamesTests(SpreadsheetDir, SimpleTestCase):
    def test_reads_names_across_repeated_header_blocks_skipping_totals(self):
        path = self.payments_workbook([["ANA SOUZA", "BRUNO LIMA"], ["CAMILA NUNES"]])

        self.assertEqual(read_payment_names(path), ["ANA SOUZA", "BRUNO LIMA", "CAMILA NUNES"])

    def test_same_person_in_two_fortnights_appears_once_in_first_spelling(self):
        path = self.payments_workbook([["Gislaine Sousa Gusmão"], ["GISLAINE SOUSA GUSMAO", "Bruno Lima"]])

        self.assertEqual(read_payment_names(path), ["Gislaine Sousa Gusmão", "Bruno Lima"])

    def test_header_is_matched_case_insensitively(self):
        path = self.payments_workbook([["ANA SOUZA"]], header="Aplicador")

        self.assertEqual(read_payment_names(path), ["ANA SOUZA"])

    def test_rows_before_the_first_header_are_ignored(self):
        # A linha de título "CONTROLE DE RPAS" vem antes de qualquer cabeçalho.
        path = self.payments_workbook([["ANA SOUZA"]])

        self.assertNotIn("CONTROLE DE RPAS", read_payment_names(path))

    def test_sheet_without_the_name_column_is_refused(self):
        path = self.payments_workbook([["ANA SOUZA"]], header="NOME")

        with self.assertRaisesMessage(ValueError, "APLICADOR"):
            read_payment_names(path)

    def test_missing_sheet_is_an_error(self):
        path = self.payments_workbook([["ANA SOUZA"]], sheet="Planilha1")

        with self.assertRaises(KeyError):
            read_payment_names(path)


class ReadProfilesTests(SpreadsheetDir, SimpleTestCase):
    def test_maps_every_column_to_the_model_field(self):
        path = self.profiles_workbook([profile_row("Ana Souza", vse="x")])

        [profile] = read_profiles(path)

        self.assertEqual(profile.name, "Ana Souza")
        self.assertEqual(profile.fields["cpf"], "123.456.789-09")
        self.assertEqual(profile.fields["birth_date"], date(2001, 3, 14))
        self.assertEqual(profile.fields["bank_branch"], "3824")
        self.assertEqual(profile.fields["bank_account"], "01090861-6")
        self.assertTrue(profile.fields["vse"])
        self.assertNotIn("bank_details", profile.fields)
        self.assertNotIn("nome", profile.fields)

    def test_vse_is_false_unless_marked_with_x(self):
        path = self.profiles_workbook([profile_row("Ana Souza", vse=""), profile_row("Bruno Lima", vse="não")])

        self.assertEqual([profile.fields["vse"] for profile in read_profiles(path)], [False, False])

    def test_rows_without_a_name_are_skipped(self):
        path = self.profiles_workbook([profile_row("Ana Souza"), profile_row(None), profile_row("Bruno Lima")])

        self.assertEqual([profile.name for profile in read_profiles(path)], ["Ana Souza", "Bruno Lima"])

    def test_short_rows_fill_missing_cells_with_blank(self):
        path = self.profiles_workbook([["Ana Souza", "31 99999-0000"]])

        [profile] = read_profiles(path)

        self.assertEqual(profile.fields["phone"], "31 99999-0000")
        self.assertEqual(profile.fields["cpf"], "")
        self.assertIsNone(profile.fields["birth_date"])

    def test_birth_date_typed_as_text_is_parsed(self):
        path = self.profiles_workbook([profile_row("Ana Souza", birth_date="14/03/2001")])

        self.assertEqual(read_profiles(path)[0].fields["birth_date"], date(2001, 3, 14))

    def test_sheet_without_the_header_row_is_refused(self):
        path = self.profiles_workbook([profile_row("Ana Souza")], header=["Coluna A", "Coluna B"])

        with self.assertRaisesMessage(ValueError, "cabeçalho"):
            read_profiles(path)

    def test_header_missing_a_column_is_refused_naming_it(self):
        header = [label for label in PROFILE_HEADER if label != "PIX"]
        path = self.profiles_workbook([], header=header)

        with self.assertRaisesMessage(ValueError, "pix_key"):
            read_profiles(path)