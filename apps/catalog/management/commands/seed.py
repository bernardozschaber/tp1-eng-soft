"""
Seeds the reference data taken from the legacy "Cadastros" sheet and creates
the default admin user. Safe to run repeatedly (idempotent).

    python manage.py seed
"""
from pathlib import Path

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
SAMPLE_LIST = Path(__file__).resolve().parents[4] / "docs" / "samples" / "lista_pagamento_exemplo.xlsx"


class Command(BaseCommand):
    help = "Seeds units, paying companies, sectors, tax rates and the admin user."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="also import docs/samples/lista_pagamento_exemplo.xlsx")

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
        if options["demo"]:
            self._import_demo(user_model.objects.get(username=DEFAULT_ADMIN["username"]))
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _import_demo(self, user) -> None:
        from apps.imports.services import import_with_defaults

        result = import_with_defaults(SAMPLE_LIST.name, SAMPLE_LIST.read_bytes(), user=user)
        self.stdout.write(f"Demo data: {result['entries']} entries, {result['applicators']} applicators.")
