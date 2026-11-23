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