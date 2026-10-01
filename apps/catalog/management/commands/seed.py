"""
Seeds the reference data taken from the legacy "Cadastros" sheet and creates
the default admin user. Safe to run repeatedly (idempotent).

    python manage.py seed

Só dados de referência: unidades, empresas pagadoras, setores, alíquotas e o
admin. Aplicadores e lançamentos entram pelos dados reais — a lista conferida
por `manage.py roster`, os lançamentos pela importação em /importar.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit

UNITS = [
    # (unit name, paying company, default on import)
    ("Lourdes", "RRPM Matriz", True),
    ("Cidade Jardim", "RRPM CJ", False),
    ("Santo Antônio", "RRPM GO", False),
    ("Vale do Sereno", "RRPM VSE", False),
]

SECTORS = [
    ("APL. DE PROVAS", True),
    ("ADM", False),
    ("CDM", False),
    ("MKT", False),
    ("PEDAGÓGICO", False),
    ("SECRETARIA - REGULATÓRIO", False),
]

DEFAULT_ADMIN = {"username": "admin", "password": "admin", "first_name": "Demo"}


class Command(BaseCommand):
    help = "Seeds units, paying companies, sectors, tax rates and the admin user."

    def handle(self, *args, **options):
        for unit_name, company_name, is_default in UNITS:
            company, _ = PayingCompany.objects.get_or_create(name=company_name)
            Unit.objects.update_or_create(
                name=unit_name, defaults={"paying_company": company, "is_default": is_default}
            )
        for sector_name, is_default in SECTORS:
            Sector.objects.update_or_create(name=sector_name, defaults={"is_default": is_default})
        TaxSettings.current()

        user_model = get_user_model()
        if not user_model.objects.filter(username=DEFAULT_ADMIN["username"]).exists():
            user_model.objects.create_superuser(**DEFAULT_ADMIN)
            self.stdout.write("Admin user created (admin / admin).")
        self.stdout.write(self.style.SUCCESS("Seed complete."))
