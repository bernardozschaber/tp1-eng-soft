"""`manage.py seed_demo`: a operação fictícia de quem abre o sistema pela primeira vez."""
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from apps.applicators.models import Applicator, RegistrationStatus
from apps.payroll.management.commands.seed_demo import (
    cpf_check_digits,
    format_cpf,
    fortnight_ranges,
)
from apps.payroll.models import ImportBatch, ServiceEntry

# Pequeno de propósito: o comando salva lançamento por lançamento, e o que se
# testa é a forma dos dados, não o volume padrão de 32 aplicadores.
DEMO_SIZE = 10


def run(command: str, **options) -> str:
    out = StringIO()
    call_command(command, stdout=out, **options)
    return out.getvalue()


class SeedDemoHelpersTests(SimpleTestCase):
    def test_cpf_check_digits_match_a_known_valid_cpf(self):
        # 529.982.247-25 é o CPF de exemplo usado em validadores.
        self.assertEqual(cpf_check_digits("529982247"), "25")

    def test_cpf_check_digit_ten_becomes_zero(self):
        # 100.000.001: soma 10*1 + 2*1 = 12, e 120 % 11 = 10 — o dígito vira 0.
        self.assertEqual(cpf_check_digits("100000001")[0], "0")

    def test_format_cpf(self):
        self.assertEqual(format_cpf("529982247"), "529.982.247-25")

    def test_fortnight_ranges_only_include_closed_fortnights(self):
        ranges = fortnight_ranges(date(2026, 3, 10), months=1)

        self.assertEqual(
            [(first, last) for first, last, _ in ranges],
            [(date(2026, 2, 1), date(2026, 2, 15)), (date(2026, 2, 16), date(2026, 2, 28))],
        )
        self.assertEqual(ranges[0][2], "1ª quinzena 02-2026")

    def test_fortnight_ranges_cross_the_year_and_end_on_the_month_last_day(self):
        ranges = fortnight_ranges(date(2026, 1, 20), months=1)

        self.assertEqual(ranges[0][:2], (date(2025, 12, 1), date(2025, 12, 15)))
        self.assertEqual(ranges[1][:2], (date(2025, 12, 16), date(2025, 12, 31)))
        self.assertEqual(ranges[-1][:2], (date(2026, 1, 1), date(2026, 1, 15)))

    def test_six_months_give_twelve_or_thirteen_fortnights(self):
        self.assertEqual(len(fortnight_ranges(date(2026, 11, 9), months=6)), 12)
        self.assertEqual(len(fortnight_ranges(date(2026, 11, 30), months=6)), 13)


class SeedDemoCommandTests(TestCase):
    def setUp(self):
        run("seed")

    def test_refuses_without_reference_data(self):
        from apps.catalog.models import Sector, Unit

        Unit.objects.all().delete()
        Sector.objects.all().delete()

        with self.assertRaisesMessage(CommandError, "manage.py seed"):
            run("seed_demo", applicators=DEMO_SIZE)

    def test_creates_applicators_and_entries_and_reports_them(self):
        output = run("seed_demo", applicators=DEMO_SIZE)

        self.assertEqual(Applicator.objects.count(), DEMO_SIZE)
        entries = ServiceEntry.objects.all()
        self.assertTrue(entries.exists())
        self.assertFalse(entries.filter(activity_date__gte=date.today()).exists())
        self.assertFalse(entries.filter(import_batch__isnull=True).exists())
        self.assertTrue(ImportBatch.objects.filter(file_name__startswith="Relatório de Atividade - ").exists())
        self.assertIn(f"{DEMO_SIZE} aplicadores", output)
        self.assertIn(f"{entries.count()} lançamentos", output)
        self.assertIn("Dados de demonstração criados.", output)

    def test_every_demo_cpf_is_valid(self):
        run("seed_demo", applicators=DEMO_SIZE)

        for cpf in Applicator.objects.values_list("cpf", flat=True):
            digits = cpf.replace(".", "").replace("-", "")
            self.assertEqual(digits[9:], cpf_check_digits(digits[:9]), cpf)

    def test_about_one_in_nine_applicators_has_no_bank_data(self):
        run("seed_demo", applicators=DEMO_SIZE)

        incomplete = Applicator.objects.filter(bank_name="")
        self.assertEqual(incomplete.count(), 2)  # índices 0 e 9 da lista ordenada
        self.assertFalse(incomplete.exclude(pix_key="").exists())
        self.assertFalse(incomplete.exclude(notes__startswith="Cadastro incompleto").exists())

    def test_late_joiners_stay_as_first_payment(self):
        run("seed_demo", applicators=DEMO_SIZE)

        # Os seis últimos só entram na quinzena mais recente; os que de fato
        # receberam algo ficam como "primeiro pagamento".
        self.assertTrue(Applicator.objects.filter(registration_status=RegistrationStatus.NEW).exists())

    def test_is_deterministic(self):
        run("seed_demo", applicators=DEMO_SIZE)
        first = (
            list(Applicator.objects.order_by("full_name").values_list("full_name", "cpf")),
            ServiceEntry.objects.count(),
        )

        run("seed_demo", applicators=DEMO_SIZE, reset=True)
        second = (
            list(Applicator.objects.order_by("full_name").values_list("full_name", "cpf")),
            ServiceEntry.objects.count(),
        )

        self.assertEqual(first, second)

    def test_refuses_to_mix_with_existing_data(self):
        Applicator.objects.create(full_name="Pessoa Real")

        with self.assertRaisesMessage(CommandError, "--reset"):
            run("seed_demo", applicators=DEMO_SIZE)

        self.assertEqual(Applicator.objects.count(), 1)

    def test_reset_replaces_existing_data(self):
        Applicator.objects.create(full_name="Pessoa Real")

        output = run("seed_demo", applicators=DEMO_SIZE, reset=True)

        self.assertFalse(Applicator.objects.filter(full_name="Pessoa Real").exists())
        self.assertEqual(Applicator.objects.count(), DEMO_SIZE)
        self.assertIn("registros antigos apagados", output)
