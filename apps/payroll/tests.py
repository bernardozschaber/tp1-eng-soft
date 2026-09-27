"""O mesmo serviço não pode ser lançado duas vezes.

Duas pessoas pagas a mais num fechamento saem caro e passam despercebidas: o
resumo só mostra um total maior. Os testes aqui cobrem os três caminhos por
onde uma repetição poderia entrar — o banco, o formulário e a importação — e o
caso vizinho que *não* é repetição e precisa continuar passando: a mesma
atividade em dois turnos do mesmo dia.
"""
import re
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.forms import ServiceEntryForm
from apps.payroll.models import DuplicateServiceEntry, ServiceEntry, ServiceRole, Shift, event_key


class DuplicateEntryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        company = PayingCompany.objects.create(name="RRPM Matriz")
        cls.unit = Unit.objects.create(name="Lourdes", paying_company=company, is_default=True)
        cls.other_unit = Unit.objects.create(name="Cidade Jardim", paying_company=company)
        cls.sector = Sector.objects.create(name="Apl. de Provas", is_default=True)
        TaxSettings.objects.create(inss_rate=Decimal("11"), iss_rate=Decimal("5"), ir_rate=Decimal("0"))
        cls.applicator = Applicator.objects.create(full_name="Joao Dario Lodi Campolina")

    def make_entry(self, **overrides):
        fields = {
            "applicator": self.applicator,
            "role": ServiceRole.ADVISOR,
            "activity_date": date(2026, 9, 8),
            "event_name": "Oficina de Redação",
            "shift": Shift.AFTERNOON,
            "sector": self.sector,
            "unit": self.unit,
            "net_amount": Decimal("87.00"),
        }
        return ServiceEntry.objects.create(**{**fields, **overrides})

    # -- a recusa na gravação --------------------------------------------

    def test_saving_the_same_service_twice_raises_with_an_explanation(self):
        first = self.make_entry()
        with self.assertRaises(DuplicateServiceEntry) as raised:
            self.make_entry()
        message = " ".join(raised.exception.messages)
        self.assertIn("Joao Dario Lodi Campolina", message)
        self.assertIn("Oficina de Redação", message)
        self.assertIn("08/09/2026", message)
        self.assertIn("Tarde", message)
        self.assertIn("Lourdes", message)
        self.assertIn(f"#{first.pk}", message)
        self.assertEqual(ServiceEntry.objects.count(), 1)

    def test_the_refusal_happens_before_the_insert(self):
        """Nada chega ao banco, então a transação de quem chamou sobrevive.

        É o que separa esta recusa de um `IntegrityError`: a importação grava
        dezenas de linhas dentro de uma transação só, e uma transação abortada
        pelo banco levaria junto tudo o que já tinha entrado.
        """
        self.make_entry()
        with self.assertRaises(DuplicateServiceEntry):
            self.make_entry(net_amount=Decimal("999.00"))
        self.make_entry(shift=Shift.MORNING)  # a transação continua utilizável
        self.assertEqual(ServiceEntry.objects.count(), 2)

    def test_accents_and_case_do_not_create_a_second_service(self):
        """"OFICINA DE REDACAO" é a mesma atividade que "Oficina de Redação"."""
        self.make_entry()
        with self.assertRaises(DuplicateServiceEntry):
            self.make_entry(event_name="  OFICINA DE REDACAO ")

    def test_the_database_refuses_it_too(self):
        """A restrição existe de verdade, para quem escrever direto na tabela.

        `bulk_create` não passa por `save()`, então é o jeito de provar que a
        garantia não depende de ninguém lembrar de chamar a checagem — um
        script de migração ou uma carga de dados esbarram nela do mesmo jeito.
        """
        self.make_entry()
        twin = ServiceEntry(
            applicator=self.applicator, role=ServiceRole.ADVISOR, activity_date=date(2026, 9, 8),
            event_name="Oficina de Redação", shift=Shift.AFTERNOON, sector=self.sector,
            unit=self.unit, net_amount=Decimal("87.00"),
        )
        twin.apply_calculations()
        with self.assertRaises(IntegrityError):
            ServiceEntry.objects.bulk_create([twin])