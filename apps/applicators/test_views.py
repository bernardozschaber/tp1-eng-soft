"""As telas de cadastro de aplicadores, pela borda de fora: `django.test.Client`."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.applicators.models import Applicator, RegistrationStatus
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.payroll.models import ServiceEntry, ServiceRole, Shift

FORM_DEFAULTS = {"registration_status": RegistrationStatus.NEW, "is_active": "on"}


class ApplicatorViewsTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin", password="admin"))
        self.ana = Applicator.objects.create(
            full_name="Ana Souza", cpf="111.222.333-44", registration_status=RegistrationStatus.ACTIVE
        )
        self.bruno = Applicator.objects.create(full_name="Bruno Lima", email="bruno@email.com")

    def add_entry(self, applicator):
        company = PayingCompany.objects.create(name="RRPM Teste")
        unit = Unit.objects.create(name="Unidade Teste", paying_company=company)
        return ServiceEntry.objects.create(
            applicator=applicator, role=ServiceRole.APPLICATOR, activity_date=date(2026, 9, 15),
            event_name="Simulado", shift=Shift.MORNING, sector=Sector.objects.create(name="SETOR"),
            unit=unit, net_amount=102,
        )

    def listed(self, **params):
        response = self.client.get("/aplicadores/", params)
        self.assertEqual(response.status_code, 200)
        return [applicator.full_name for applicator in response.context["page"]]

    # --- lista -----------------------------------------------------------

    def test_list_shows_everyone_with_status_counts(self):
        response = self.client.get("/aplicadores/")

        self.assertEqual(self.listed(), ["Ana Souza", "Bruno Lima"])
        self.assertEqual((response.context["new_count"], response.context["active_count"]), (1, 1))

    def test_search_by_name_cpf_or_email(self):
        self.assertEqual(self.listed(q="souza"), ["Ana Souza"])
        self.assertEqual(self.listed(q="222.333"), ["Ana Souza"])
        self.assertEqual(self.listed(q="bruno@"), ["Bruno Lima"])

    def test_filter_by_status_and_inactive(self):
        Applicator.objects.filter(pk=self.bruno.pk).update(is_active=False)

        self.assertEqual(self.listed(status=RegistrationStatus.ACTIVE), ["Ana Souza"])
        self.assertEqual(self.listed(status="inactive"), ["Bruno Lima"])
        self.assertEqual(self.listed(status="qualquer"), ["Ana Souza", "Bruno Lima"])

    # --- criar e editar -------------------------------------------------

    def test_create_redirects_to_the_new_record(self):
        response = self.client.post("/aplicadores/novo/", {**FORM_DEFAULTS, "full_name": "  Camila   Nunes "})

        camila = Applicator.objects.get(full_name="Camila Nunes")
        self.assertRedirects(response, f"/aplicadores/{camila.pk}/", fetch_redirect_response=False)

    def test_create_refuses_a_name_that_differs_only_by_accent(self):
        response = self.client.post("/aplicadores/novo/", {**FORM_DEFAULTS, "full_name": "ANA SOUZÁ"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Já existe um aplicador com este nome: Ana Souza.", response.context["form"].errors["full_name"])
        self.assertEqual(Applicator.objects.count(), 2)

    def test_create_form_renders(self):
        self.assertEqual(self.client.get("/aplicadores/novo/").status_code, 200)

    def test_update_saves_and_keeping_the_own_name_is_not_a_clash(self):
        response = self.client.post(
            f"/aplicadores/{self.ana.pk}/editar/", {**FORM_DEFAULTS, "full_name": "Ana Souza", "cpf": "999"}
        )

        self.assertRedirects(response, f"/aplicadores/{self.ana.pk}/", fetch_redirect_response=False)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.cpf, "999")

    def test_update_of_unknown_applicator_is_404(self):
        self.assertEqual(self.client.get("/aplicadores/999/editar/").status_code, 404)

    # --- ficha, histórico e exclusão -------------------------------------

    def test_card_and_detail_render(self):
        self.add_entry(self.ana)

        self.assertEqual(self.client.get(f"/aplicadores/{self.ana.pk}/ficha/").status_code, 200)
        response = self.client.get(f"/aplicadores/{self.ana.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["count"], 1)

    def test_delete_without_entries(self):
        response = self.client.post(f"/aplicadores/{self.bruno.pk}/excluir/")

        self.assertRedirects(response, "/aplicadores/", fetch_redirect_response=False)
        self.assertFalse(Applicator.objects.filter(pk=self.bruno.pk).exists())

    def test_delete_refuses_who_was_already_paid(self):
        self.add_entry(self.ana)

        response = self.client.post(f"/aplicadores/{self.ana.pk}/excluir/", follow=True)

        self.assertTrue(Applicator.objects.filter(pk=self.ana.pk).exists())
        self.assertContains(response, "tem 1 lançamento(s) e não pode ser excluído(a)")
