"""`manage.py seed_demo`: a operação fictícia de quem abre o sistema pela primeira vez."""
from datetime import date

from django.test import SimpleTestCase

from apps.payroll.management.commands.seed_demo import (
    cpf_check_digits,
    format_cpf,
    fortnight_ranges,
)


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