"""A conta do RPA: do líquido prometido ao bruto, e do bruto aos descontos.

É o cálculo que o sistema existe para fazer. Um centavo errado aqui se repete
em todo lançamento de todo aplicador, e o resumo continua fechando — só que
com o número errado.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.payroll.calculator import PayrollBreakdown, TaxRates, compute_breakdown

STANDARD = TaxRates.from_percentages(Decimal("11"), Decimal("5"))


class TaxRatesTests(SimpleTestCase):
    def test_percentages_become_fractions(self):
        """O cadastro guarda 11 e 5; a conta precisa de 0,11 e 0,05."""
        self.assertEqual(STANDARD.inss, Decimal("0.11"))
        self.assertEqual(STANDARD.iss, Decimal("0.05"))
        self.assertEqual(STANDARD.ir, Decimal("0"))

    def test_the_applicator_keeps_84_percent_of_the_gross(self):
        self.assertEqual(STANDARD.net_factor, Decimal("0.84"))


class ComputeBreakdownTests(SimpleTestCase):
    def test_the_gross_up_returns_exactly_the_promised_net(self):
        """R$ 87,00 de orientação: o aplicador tem de receber R$ 87,00, não um centavo a menos."""
        breakdown = compute_breakdown(Decimal("87.00"), STANDARD)
        self.assertEqual(breakdown.gross_amount, Decimal("103.57"))
        self.assertEqual(breakdown.inss_amount, Decimal("11.39"))
        self.assertEqual(breakdown.iss_amount, Decimal("5.18"))
        self.assertEqual(breakdown.ir_amount, Decimal("0.00"))
        self.assertEqual(breakdown.net_payable, Decimal("87.00"))
        self.assertEqual(breakdown.difference, Decimal("0.00"))

    def test_every_amount_is_rounded_to_cents(self):
        breakdown = compute_breakdown(Decimal("100"), STANDARD)
        self.assertEqual(breakdown.gross_amount, Decimal("119.05"))
        self.assertEqual(breakdown.total_withheld, Decimal("19.05"))
        for amount in (breakdown.gross_amount, breakdown.inss_amount, breakdown.iss_amount):
            self.assertEqual(amount.as_tuple().exponent, -2)

    def test_rounding_noise_is_reported_and_not_adjusted(self):
        """O financeiro decidiu não aplicar o ajuste de ±R$ 0,01 da planilha antiga."""
        breakdown = compute_breakdown(Decimal("50.00"), STANDARD)
        self.assertEqual(breakdown.gross_amount, Decimal("59.52"))
        self.assertEqual(breakdown.net_payable, Decimal("49.99"))
        self.assertEqual(breakdown.difference, Decimal("-0.01"))
        self.assertTrue(breakdown.is_consistent)

    def test_ir_is_withheld_when_its_rate_is_set(self):
        rates = TaxRates.from_percentages(Decimal("11"), Decimal("5"), Decimal("7.5"))
        breakdown = compute_breakdown(Decimal("76.50"), rates)
        self.assertEqual(breakdown.gross_amount, Decimal("100.00"))
        self.assertEqual(breakdown.ir_amount, Decimal("7.50"))
        self.assertEqual(breakdown.net_payable, Decimal("76.50"))

    def test_zero_net_produces_zero_everywhere(self):
        breakdown = compute_breakdown(Decimal("0"), STANDARD)
        self.assertEqual(breakdown.gross_amount, Decimal("0.00"))
        self.assertEqual(breakdown.total_withheld, Decimal("0.00"))

    def test_rates_of_100_percent_or_more_are_refused(self):
        """Sem a recusa, a conta divide por zero ou gera bruto negativo."""
        for ir in ("84", "90"):
            with self.subTest(ir=ir), self.assertRaises(ValueError):
                compute_breakdown(Decimal("10"), TaxRates.from_percentages(Decimal("11"), Decimal("5"), Decimal(ir)))


class ConsistencyTests(SimpleTestCase):
    def make(self, net_payable_gap: str) -> PayrollBreakdown:
        gross = Decimal("100.00")
        return PayrollBreakdown(
            net_amount=Decimal("84.00") - Decimal(net_payable_gap),
            gross_amount=gross,
            inss_amount=Decimal("11.00"),
            iss_amount=Decimal("5.00"),
            ir_amount=Decimal("0.00"),
        )

    def test_a_gap_below_one_real_is_consistent(self):
        self.assertTrue(self.make("0.99").is_consistent)

    def test_a_gap_of_one_real_is_flagged(self):
        """É a conferência que a planilha de controle fazia à mão (história 7)."""
        self.assertFalse(self.make("1.00").is_consistent)
        self.assertFalse(self.make("-1.00").is_consistent)
