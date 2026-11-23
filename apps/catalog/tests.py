"""`manage.py seed`: os dados de referência que todo o resto do sistema supõe."""
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.catalog.management.commands.seed import SECTORS, UNITS
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit


def run_seed() -> str:
    out = StringIO()
    call_command("seed", stdout=out)
    return out.getvalue()


class SeedCommandTests(TestCase):
    def test_creates_every_unit_with_its_paying_company(self):
        run_seed()

        for unit_name, company_name, is_default in UNITS:
            unit = Unit.objects.get(name=unit_name)
            self.assertEqual(unit.paying_company.name, company_name)
            self.assertEqual(unit.is_default, is_default)

    def test_exactly_one_default_unit_and_one_default_sector(self):
        # A importação usa o padrão quando a planilha não diz a unidade/setor:
        # dois padrões e ela escolheria um ao acaso.
        run_seed()

        self.assertEqual(Unit.objects.filter(is_default=True).count(), 1)
        self.assertEqual(Sector.objects.filter(is_default=True).count(), 1)
        self.assertEqual(Sector.objects.get(is_default=True).name, "APL. DE PROVAS")

    def test_creates_every_sector_and_the_tax_settings_row(self):
        run_seed()

        self.assertEqual(
            set(Sector.objects.values_list("name", flat=True)) & {name for name, _ in SECTORS},
            {name for name, _ in SECTORS},
        )
        self.assertTrue(TaxSettings.objects.filter(pk=1).exists())

    def test_creates_the_admin_superuser(self):
        output = run_seed()

        admin = get_user_model().objects.get(username="admin")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("admin"))
        self.assertIn("Admin user created", output)

    def test_is_idempotent(self):
        run_seed()
        counts = (Unit.objects.count(), PayingCompany.objects.count(), Sector.objects.count())

        output = run_seed()

        self.assertEqual((Unit.objects.count(), PayingCompany.objects.count(), Sector.objects.count()), counts)
        self.assertEqual(get_user_model().objects.filter(username="admin").count(), 1)
        self.assertNotIn("Admin user created", output)
        self.assertIn("Seed complete.", output)

    def test_does_not_reset_an_existing_admin_password(self):
        get_user_model().objects.create_superuser("admin", password="trocada")

        run_seed()

        self.assertTrue(get_user_model().objects.get(username="admin").check_password("trocada"))

    def test_restores_the_default_flag_moved_by_hand(self):
        run_seed()
        Unit.objects.filter(name="Lourdes").update(is_default=False)
        Unit.objects.filter(name="Cidade Jardim").update(is_default=True)

        run_seed()

        self.assertEqual(Unit.objects.get(is_default=True).name, "Lourdes")


class SettingsPageTests(TestCase):
    def setUp(self):
        run_seed()
        self.client.force_login(get_user_model().objects.get(username="admin"))

    def test_page_shows_the_breakdown_of_a_100_net_example(self):
        response = self.client.get("/configuracoes/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["example"].net_amount, 100)

    def test_saves_tax_rates(self):
        response = self.client.post("/configuracoes/", {"form": "tax", "inss_rate": "11", "iss_rate": "5", "ir_rate": "0"})

        self.assertRedirects(response, "/configuracoes/", fetch_redirect_response=False)
        self.assertEqual(TaxSettings.current().inss_rate, 11)

    def test_refuses_rates_adding_up_to_100(self):
        response = self.client.post("/configuracoes/", {"form": "tax", "inss_rate": "60", "iss_rate": "40", "ir_rate": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("menor que 100%", str(response.context["tax_form"].non_field_errors()))

    def test_creates_a_unit_and_a_sector(self):
        company = PayingCompany.objects.first()

        self.client.post("/configuracoes/", {"form": "unit", "name": "Unidade Nova", "paying_company": company.pk})
        self.client.post("/configuracoes/", {"form": "sector", "name": "SETOR NOVO"})

        self.assertTrue(Unit.objects.filter(name="Unidade Nova", paying_company=company).exists())
        self.assertTrue(Sector.objects.filter(name="SETOR NOVO").exists())

    def test_invalid_unit_stays_on_the_page(self):
        response = self.client.post("/configuracoes/", {"form": "unit", "name": ""})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["unit_form"].errors)

    def test_set_default_leaves_exactly_one(self):
        jardim = Unit.objects.get(name="Cidade Jardim")
        adm = Sector.objects.get(name="ADM")

        self.client.post(f"/configuracoes/padrao/unit/{jardim.pk}/")
        self.client.post(f"/configuracoes/padrao/sector/{adm.pk}/")

        self.assertEqual(list(Unit.objects.filter(is_default=True)), [jardim])
        self.assertEqual(list(Sector.objects.filter(is_default=True)), [adm])

    def test_set_default_of_unknown_pk_is_404(self):
        self.assertEqual(self.client.post("/configuracoes/padrao/unit/999/").status_code, 404)
