"""O calendário de pagamento: dia 1 a 15 paga no dia 5, dia 16 em diante no 20.

Um erro aqui não muda o valor de ninguém, muda *quando* ele é pago: o
lançamento cai no fechamento errado e some do resumo da quinzena em que o
financeiro o procura.
"""
from datetime import date

from django.test import SimpleTestCase

from apps.payroll.schedule import fortnight_label, payment_date_for


class PaymentDateTests(SimpleTestCase):
    def test_the_15th_is_still_paid_on_the_5th(self):
        """O dia 15 é a borda da primeira quinzena; jogá-lo para o dia 20 atrasa o pagamento."""
        self.assertEqual(payment_date_for(date(2026, 9, 15)), date(2026, 10, 5))

    def test_the_16th_is_paid_on_the_20th(self):
        self.assertEqual(payment_date_for(date(2026, 9, 16)), date(2026, 10, 20))

    def test_the_first_and_last_day_of_a_month_land_in_different_cycles(self):
        self.assertEqual(payment_date_for(date(2026, 2, 1)), date(2026, 3, 5))
        self.assertEqual(payment_date_for(date(2026, 2, 28)), date(2026, 3, 20))

    def test_december_is_paid_in_january_of_the_next_year(self):
        """A virada de ano é onde `month + 1` vira 13 e o cálculo quebra."""
        self.assertEqual(payment_date_for(date(2026, 12, 1)), date(2027, 1, 5))
        self.assertEqual(payment_date_for(date(2026, 12, 31)), date(2027, 1, 20))


class FortnightLabelTests(SimpleTestCase):
    def test_a_payment_on_the_5th_closes_the_first_half_of_the_previous_month(self):
        """É o título de cada bloco do Resumo exportado; vazio, a contabilidade não sabe o que está pagando."""
        self.assertEqual(fortnight_label(date(2026, 10, 5)), "1ª quinzena de Setembro")

    def test_a_payment_on_the_20th_closes_the_second_half(self):
        self.assertEqual(fortnight_label(date(2026, 10, 20)), "2ª quinzena de Setembro")

    def test_january_payments_name_december_of_the_previous_year(self):
        self.assertEqual(fortnight_label(date(2027, 1, 20), with_year=True), "2ª quinzena de Dezembro/2026")

    def test_the_label_and_the_payment_date_agree(self):
        """O rótulo da data de pagamento precisa nomear a quinzena em que a atividade aconteceu."""
        activity = date(2026, 3, 22)
        self.assertEqual(fortnight_label(payment_date_for(activity)), "2ª quinzena de Março")
