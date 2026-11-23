"""`manage.py roster` e a leitura das planilhas do setor que ele usa.

As planilhas reais (controle de RPAs e agendamento) têm dados pessoais e não
entram no repositório. Os testes montam em disco planilhas com o mesmo layout —
o cabeçalho repetido a cada quinzena, as linhas de TOTAL, a ficha com o
cabeçalho na linha 2 — e nomes, CPFs e contas inventados.
"""
import shutil
import tempfile
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from openpyxl import Workbook

from apps.applicators.models import Applicator, RegistrationStatus
from apps.applicators.spreadsheets import (
    PAYMENTS_SHEET,
    PROFILE_COLUMNS,
    PROFILES_SHEET,
    Profile,
    _as_date,
    _split_bank_details,
    _text,
    match_profiles,
    read_payment_names,
    read_profiles,
)
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.payroll.models import ServiceEntry, ServiceRole, Shift

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


class MatchProfilesTests(SimpleTestCase):
    def test_exact_match_ignores_accents_and_case(self):
        profile = Profile("Gislaine Sousa Gusmão")

        matched, ambiguous = match_profiles(["GISLAINE SOUSA GUSMAO"], [profile])

        self.assertEqual(matched, {"GISLAINE SOUSA GUSMAO": profile})
        self.assertEqual(ambiguous, {})

    def test_shorter_spelling_matches_the_single_longer_profile(self):
        profile = Profile("Isadora Godinho Andrade")

        matched, _ = match_profiles(["Isadora Godinho"], [profile, Profile("Bruno Lima")])

        self.assertEqual(matched["ISADORA GODINHO"], profile)

    def test_name_matching_two_profiles_is_ambiguous_not_matched(self):
        # Escolher a primeira escreveria o CPF de uma pessoa na ficha de outra.
        profiles = [Profile("Ana Maria Souza"), Profile("Ana Clara Souza")]

        matched, ambiguous = match_profiles(["Ana Souza"], profiles)

        self.assertEqual(matched, {})
        self.assertEqual(ambiguous, {"ANA SOUZA": profiles})

    def test_name_without_profile_is_neither(self):
        matched, ambiguous = match_profiles(["Bruno Lima"], [Profile("Ana Souza")])

        self.assertEqual((matched, ambiguous), ({}, {}))


# --- o comando ---------------------------------------------------------------


def run_roster(*args, **options) -> str:
    out = StringIO()
    call_command("roster", *args, stdout=out, **options)
    return out.getvalue()


class RosterArgumentTests(TestCase):
    def test_requires_a_source(self):
        with self.assertRaisesMessage(CommandError, "OU --payments"):
            run_roster()

    def test_refuses_names_file_and_payments_together(self):
        with self.assertRaisesMessage(CommandError, "OU --payments"):
            run_roster("nomes.txt", payments="RPAS.xlsx")

    def test_profiles_requires_payments(self):
        with self.assertRaisesMessage(CommandError, "--profiles só faz sentido"):
            run_roster("nomes.txt", profiles="Agendamento.xlsx")


class RosterFromNamesFileTests(SpreadsheetDir, TestCase):
    def write_names(self, text: str) -> str:
        path = self.make_dir() / "nomes.txt"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_creates_active_applicators_with_display_names(self):
        path = self.write_names("ANA LUISA DE SOUZA\nbruno   lima\n")

        output = run_roster(path)

        self.assertEqual(
            sorted(Applicator.objects.values_list("full_name", flat=True)),
            ["Ana Luisa de Souza", "Bruno Lima"],
        )
        self.assertFalse(Applicator.objects.exclude(registration_status=RegistrationStatus.ACTIVE).exists())
        self.assertIn("2 cadastro(s) criado(s), 0 atualizado(s).", output)

    def test_skips_blank_lines_comments_and_repeated_spellings(self):
        path = self.write_names("# lista conferida em 09/2026\n\nGislaine Sousa Gusmão\nGISLAINE SOUSA GUSMAO\n")

        run_roster(path)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Gislaine Sousa Gusmão"])

    def test_reads_from_stdin_with_dash(self):
        with mock.patch("sys.stdin", StringIO("Ana Souza\nBruno Lima\n")):
            run_roster("-")

        self.assertEqual(Applicator.objects.count(), 2)

    def test_empty_input_is_an_error(self):
        path = self.write_names("# nada aqui\n\n")

        with self.assertRaisesMessage(CommandError, "Nenhum nome"):
            run_roster(path)

    def test_existing_new_applicator_is_promoted_to_active(self):
        Applicator.objects.create(full_name="ANA SOUZA", registration_status=RegistrationStatus.NEW)
        path = self.write_names("Ana Souza\n")

        output = run_roster(path)

        applicator = Applicator.objects.get()
        self.assertEqual(applicator.full_name, "Ana Souza")
        self.assertEqual(applicator.registration_status, RegistrationStatus.ACTIVE)
        self.assertIn("0 cadastro(s) criado(s), 1 atualizado(s).", output)


class RosterReplaceTests(SpreadsheetDir, TestCase):
    def setUp(self):
        self.names = self.make_dir() / "nomes.txt"
        self.names.write_text("Bruno Lima\n", encoding="utf-8")

    def test_replace_deletes_the_old_roster_first(self):
        Applicator.objects.create(full_name="Pessoa Antiga")

        output = run_roster(str(self.names), replace=True)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Bruno Lima"])
        self.assertIn("1 cadastro(s) antigo(s) removido(s).", output)

    def test_replace_refuses_while_entries_exist_and_changes_nothing(self):
        company = PayingCompany.objects.create(name="RRPM Teste")
        unit = Unit.objects.create(name="Unidade Teste", paying_company=company)
        sector = Sector.objects.create(name="SETOR TESTE")
        old = Applicator.objects.create(full_name="Pessoa Antiga")
        ServiceEntry.objects.create(
            applicator=old, role=ServiceRole.APPLICATOR, activity_date=date(2026, 9, 15),
            event_name="Simulado", shift=Shift.MORNING, sector=sector, unit=unit, net_amount=102,
        )

        with self.assertRaisesMessage(CommandError, "1 lançamento(s)"):
            run_roster(str(self.names), replace=True)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Pessoa Antiga"])


class RosterFromSpreadsheetsTests(SpreadsheetDir, TestCase):
    def test_payments_alone_creates_bare_applicators(self):
        payments = self.payments_workbook([["ANA SOUZA", "BRUNO LIMA"], ["ANA SOUZA"]])

        output = run_roster(payments=payments)

        self.assertEqual(Applicator.objects.count(), 2)
        self.assertEqual(Applicator.objects.get(full_name="Ana Souza").cpf, "")
        self.assertNotIn("ficha", output)

    def test_profiles_fill_the_matching_applicator(self):
        payments = self.payments_workbook([["ANA SOUZA", "BRUNO LIMA"]])
        profiles = self.profiles_workbook([profile_row("Ana Souza", cpf="111.222.333-44")])

        output = run_roster(payments=payments, profiles=profiles)

        ana = Applicator.objects.get(full_name="Ana Souza")
        self.assertEqual(ana.cpf, "111.222.333-44")
        self.assertEqual(ana.bank_branch, "3824")
        self.assertEqual(ana.birth_date, date(2001, 3, 14))
        self.assertEqual(Applicator.objects.get(full_name="Bruno Lima").cpf, "")
        self.assertIn("1 cadastro(s) com ficha completa, de 1 ficha(s) lidas.", output)
        self.assertIn("1 nome(s) sem ficha correspondente.", output)

    def test_two_spellings_of_one_profile_become_one_applicator_named_by_the_profile(self):
        payments = self.payments_workbook([["ISADORA GODINHO"], ["ISADORA GODINHO ANDRADE"]])
        profiles = self.profiles_workbook([profile_row("Isadora Godinho Andrade")])

        output = run_roster(payments=payments, profiles=profiles)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Isadora Godinho Andrade"])
        self.assertIn("1 grafia(s) juntada(s)", output)

    def test_ambiguous_name_gets_no_profile_and_is_reported(self):
        payments = self.payments_workbook([["ANA SOUZA"]])
        profiles = self.profiles_workbook([profile_row("Ana Maria Souza"), profile_row("Ana Clara Souza")])

        output = run_roster(payments=payments, profiles=profiles)

        ana = Applicator.objects.get()
        self.assertEqual(ana.full_name, "Ana Souza")
        self.assertEqual(ana.cpf, "")
        self.assertIn("Ambíguo, ficha não aplicada: ANA SOUZA casa com Ana Maria Souza, Ana Clara Souza.", output)

    def test_profile_without_payment_creates_nobody(self):
        # A ficha só completa quem a planilha de pagamentos trouxe.
        payments = self.payments_workbook([["BRUNO LIMA"]])
        profiles = self.profiles_workbook([profile_row("Ana Souza")])

        run_roster(payments=payments, profiles=profiles)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Bruno Lima"])
