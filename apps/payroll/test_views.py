"""As telas de lançamento: lista, formulário, exclusão, resumo e exportação."""
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from openpyxl import load_workbook

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.payroll.models import ServiceEntry, ServiceRole, Shift

ACTIVITY = date(2026, 9, 15)


class EntryViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", password="admin")
        self.client.force_login(self.user)
        company = PayingCompany.objects.create(name="RRPM Teste")
        self.unit = Unit.objects.create(name="Unidade Teste", paying_company=company, is_default=True)
        self.sector = Sector.objects.create(name="APL. TESTE", is_default=True)
        self.ana = Applicator.objects.create(full_name="Ana Souza")
        self.entry = self.make_entry(self.ana, Shift.MORNING)

    def make_entry(self, applicator, shift, amount=102):
        return ServiceEntry.objects.create(
            applicator=applicator, role=ServiceRole.APPLICATOR, activity_date=ACTIVITY, event_name="Simulado",
            shift=shift, sector=self.sector, unit=self.unit, net_amount=amount,
        )

    def form_data(self, **overrides):
        data = {
            "applicator": self.ana.pk, "role": ServiceRole.APPLICATOR, "activity_date": "2026-09-15",
            "event_name": "Simulado", "segment": "", "shift": Shift.AFTERNOON, "sector": self.sector.pk,
            "unit": self.unit.pk, "net_amount": "150.00", "payment_date": "", "notes": "",
        }
        data.update(overrides)
        return data

    # --- lista -----------------------------------------------------------

    def test_list_shows_entries_and_totals(self):
        self.make_entry(self.ana, Shift.AFTERNOON, amount=50)

        response = self.client.get("/lancamentos/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["entries"]), 2)
        self.assertEqual(response.context["totals"]["net"], Decimal("152"))

    def test_list_inconsistent_only_hides_consistent_rows(self):
        response = self.client.get("/lancamentos/", {"inconsistent": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["entries"], [])

    # --- formulário -------------------------------------------------------

    def test_create_form_starts_with_today(self):
        response = self.client.get("/lancamentos/novo/")

        self.assertEqual(response.context["form"].initial["activity_date"], date.today())

    def test_create_records_the_author_and_computes_payment_date(self):
        response = self.client.post("/lancamentos/novo/", self.form_data())

        self.assertRedirects(response, "/lancamentos/", fetch_redirect_response=False)
        created = ServiceEntry.objects.get(shift=Shift.AFTERNOON)
        self.assertEqual(created.created_by, self.user)
        self.assertIsNotNone(created.payment_date)
        self.assertGreater(created.gross_amount, created.net_amount)

    def test_create_refuses_the_same_service_twice(self):
        response = self.client.post("/lancamentos/novo/", self.form_data(shift=Shift.MORNING))

        self.assertEqual(response.status_code, 200)
        self.assertIn("não pode ser lançado duas vezes", str(response.context["form"].non_field_errors()))
        self.assertEqual(ServiceEntry.objects.count(), 1)

    def test_create_refuses_zero_amount(self):
        response = self.client.post("/lancamentos/novo/", self.form_data(net_amount="0"))

        self.assertIn("maior que zero", str(response.context["form"].errors["net_amount"]))

    def test_update_changes_the_amount(self):
        response = self.client.post(
            f"/lancamentos/{self.entry.pk}/editar/", self.form_data(shift=Shift.MORNING, net_amount="200")
        )

        self.assertRedirects(response, "/lancamentos/", fetch_redirect_response=False)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.net_amount, Decimal("200"))

    def test_update_form_renders(self):
        self.assertEqual(self.client.get(f"/lancamentos/{self.entry.pk}/editar/").status_code, 200)

    # --- exclusão ---------------------------------------------------------

    def test_delete_goes_back_to_next(self):
        response = self.client.post(f"/lancamentos/{self.entry.pk}/excluir/", {"next": "/lancamentos/resumo/"})

        self.assertRedirects(response, "/lancamentos/resumo/", fetch_redirect_response=False)
        self.assertFalse(ServiceEntry.objects.exists())

    def test_delete_without_next_goes_to_the_list(self):
        response = self.client.post(f"/lancamentos/{self.entry.pk}/excluir/")

        self.assertRedirects(response, "/lancamentos/", fetch_redirect_response=False)

    # --- resumo e exportação ---------------------------------------------

    def test_summary_groups_the_payment_run(self):
        response = self.client.get("/lancamentos/resumo/", {"payment_date": f"{self.entry.payment_date:%Y-%m-%d}"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["net"], Decimal("102"))

    def test_summary_inconsistent_only_drops_empty_groups(self):
        response = self.client.get(
            "/lancamentos/resumo/",
            {"payment_date": f"{self.entry.payment_date:%Y-%m-%d}", "inconsistent": "1"},
        )

        self.assertEqual(response.context["groups"], [])

    def test_export_is_an_xlsx_named_after_the_payment_date(self):
        response = self.client.get("/lancamentos/exportar/", {"payment_date": f"{self.entry.payment_date:%Y-%m-%d}"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'BernoulliPay_pgto_{self.entry.payment_date:%Y-%m-%d}.xlsx', response["Content-Disposition"])
        workbook = load_workbook(BytesIO(response.content))
        self.assertGreaterEqual(len(workbook.sheetnames), 2)

    def test_all_payment_dates_summary_shows_every_run_not_the_latest(self):
        """Escolher "Todas as datas de pgto" no filtro não pode voltar para a mais recente."""
        later = ServiceEntry.objects.create(
            applicator=self.ana, role=ServiceRole.APPLICATOR, activity_date=date(2026, 9, 20),
            event_name="Simulado", shift=Shift.MORNING, sector=self.sector, unit=self.unit, net_amount=102,
        )
        self.assertNotEqual(later.payment_date, self.entry.payment_date)

        response = self.client.get("/lancamentos/resumo/", {"payment_date": ""})

        self.assertEqual([group.payment_date for group in response.context["groups"]],
                         sorted([self.entry.payment_date, later.payment_date]))
        self.assertEqual(response.context["totals"]["net"], Decimal("204"))
        self.assertContains(response, "todas as datas de pagamento")

    def test_export_of_all_payment_dates_is_named_todas(self):
        response = self.client.get("/lancamentos/exportar/", {"payment_date": ""})

        self.assertIn('BernoulliPay_pgto_todas.xlsx', response["Content-Disposition"])
