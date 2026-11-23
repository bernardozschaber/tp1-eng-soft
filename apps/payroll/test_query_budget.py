"""O número de consultas de cada tela não cresce com o histórico.

A seção 1 do TESTES.md levou o Resumo de 35,8s para 2,4s e o export de 164s
para 6,4s tirando consultas feitas por linha. Um `entry.applicator` esquecido
num template traz o N+1 de volta sem quebrar nada — só fica lento de novo,
meses depois, quando o histórico crescer. Aqui o crescimento é simulado.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.models import ServiceEntry, ServiceRole

PAGES = ("payroll:entry_list", "payroll:summary", "payroll:export")


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = PayingCompany.objects.create(name="RRPM Matriz")
        cls.units = [
            Unit.objects.create(name="Lourdes", paying_company=company, is_default=True),
            Unit.objects.create(name="Cidade Jardim", paying_company=PayingCompany.objects.create(name="RRPM CJ")),
        ]
        cls.sector = Sector.objects.create(name="Apl. de Provas", is_default=True)
        TaxSettings.objects.create(inss_rate=Decimal("11"), iss_rate=Decimal("5"), ir_rate=Decimal("0"))
        cls.user = get_user_model().objects.create_superuser("admin", password="x")

    def add_history(self, applicators: int, start: int = 0) -> None:
        """Cada aplicador trabalha nas duas unidades, nas duas quinzenas de setembro."""
        for index in range(start, start + applicators):
            person = Applicator.objects.create(full_name=f"Aplicador Ficticio {index:03d}")
            for offset, unit in enumerate(self.units):
                for day in (3, 18):
                    ServiceEntry.objects.create(
                        applicator=person, role=ServiceRole.APPLICATOR,
                        activity_date=date(2026, 9, day) + timedelta(days=offset),
                        event_name="Prova Regular", sector=self.sector, unit=unit,
                        net_amount=Decimal("84.00"),
                    )

    def count_queries(self, name: str) -> int:
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(reverse(name))
        self.assertEqual(response.status_code, 200, name)
        return len(captured)

    def test_pages_cost_the_same_with_three_times_the_history(self):
        """Mesma garantia da seção 1.6 (4x os dados, mesmos números), agora verificada a cada push."""
        self.client.force_login(self.user)
        self.add_history(5)
        small = {name: self.count_queries(name) for name in PAGES}
        self.add_history(10, start=5)
        large = {name: self.count_queries(name) for name in PAGES}
        for name in PAGES:
            with self.subTest(page=name):
                self.assertEqual(large[name], small[name])
