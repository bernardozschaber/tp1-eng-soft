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
from django.contrib.auth.models import Group
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

    def test_event_key_is_the_canonical_spelling(self):
        entry = self.make_entry(event_name="  Oficina   de Redação  ")
        self.assertEqual(entry.event_name, "Oficina   de Redação")
        self.assertEqual(entry.event_key, "OFICINA DE REDACAO")
        self.assertEqual(event_key("oficina de redacao"), entry.event_key)

    # -- o que não é repetição e precisa passar --------------------------

    def test_morning_and_afternoon_of_the_same_activity_are_two_services(self):
        """O caso que a planilha de controle mostra: dois turnos, dois valores.

        Na "LISTAGEM DE SERVIÇOS PRESTADOS" a mesma pessoa aparece duas vezes na
        Oficina de Redação do mesmo dia, com valores diferentes — ela trabalhou
        de manhã e à tarde. Confundir isso com duplicata tiraria meio dia de
        pagamento de alguém.
        """
        self.make_entry(shift=Shift.AFTERNOON, net_amount=Decimal("84.00"))
        self.make_entry(shift=Shift.MORNING, net_amount=Decimal("93.00"))
        self.assertEqual(ServiceEntry.objects.count(), 2)

    def test_different_role_unit_date_or_activity_are_separate_services(self):
        self.make_entry()
        self.make_entry(role=ServiceRole.APPLICATOR)
        self.make_entry(unit=self.other_unit)
        self.make_entry(activity_date=date(2026, 9, 15))
        self.make_entry(event_name="Prova Regular")
        self.assertEqual(ServiceEntry.objects.count(), 5)

    # -- o aviso antes da gravação ---------------------------------------

    def test_find_duplicate_points_at_the_existing_entry(self):
        existing = self.make_entry()
        found = ServiceEntry.find_duplicate(
            applicator=self.applicator, activity_date=date(2026, 9, 8),
            event_name="oficina de redacao", shift=Shift.AFTERNOON,
            role=ServiceRole.ADVISOR, unit=self.unit,
        )
        self.assertEqual(found, existing)

    def test_find_duplicate_lets_an_edit_save_over_itself(self):
        existing = self.make_entry()
        self.assertIsNone(ServiceEntry.find_duplicate(
            applicator=self.applicator, activity_date=existing.activity_date,
            event_name=existing.event_name, shift=existing.shift,
            role=existing.role, unit=existing.unit, exclude_pk=existing.pk,
        ))

    # -- o formulário manual ---------------------------------------------

    def _form_data(self, **overrides):
        data = {
            "applicator": self.applicator.pk, "role": ServiceRole.ADVISOR,
            "activity_date": "2026-09-08", "event_name": "Oficina de Redação",
            "segment": "", "shift": Shift.AFTERNOON, "sector": self.sector.pk,
            "unit": self.unit.pk, "net_amount": "87.00", "payment_date": "", "notes": "",
        }
        return {**data, **overrides}

    def test_form_refuses_a_repeated_entry_with_a_readable_message(self):
        existing = self.make_entry()
        form = ServiceEntryForm(data=self._form_data())
        self.assertFalse(form.is_valid())
        message = " ".join(form.errors["__all__"])
        self.assertIn(f"#{existing.pk}", message)
        self.assertIn("não pode ser lançado duas vezes", message)

    def test_form_accepts_the_other_shift(self):
        self.make_entry(shift=Shift.AFTERNOON)
        form = ServiceEntryForm(data=self._form_data(shift=Shift.MORNING))
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_an_entry_without_changing_it_still_validates(self):
        existing = self.make_entry()
        form = ServiceEntryForm(data=self._form_data(net_amount="90.00"), instance=existing)
        self.assertTrue(form.is_valid(), form.errors)

    def test_model_validation_reports_the_constraint(self):
        """full_clean também barra, para quem grava fora do formulário."""
        self.make_entry()
        twin = ServiceEntry(
            applicator=self.applicator, role=ServiceRole.ADVISOR, activity_date=date(2026, 9, 8),
            event_name="Oficina de Redação", shift=Shift.AFTERNOON, sector=self.sector,
            unit=self.unit, net_amount=Decimal("87.00"),
        )
        twin.apply_calculations()
        with self.assertRaises(ValidationError):
            twin.validate_constraints()


class ShiftColumnTests(TestCase):
    """A lista mostra o turno ao lado da data.

    A coluna existe por causa das duplicatas: sem ela, duas linhas iguais na
    tela podem ser a mesma oficina lançada duas vezes ou a oficina da manhã e a
    da tarde, e não há como saber olhando. Com o turno à vista, quem confere
    decide em um segundo.
    """

    @classmethod
    def setUpTestData(cls):
        company = PayingCompany.objects.create(name="RRPM Matriz")
        cls.unit = Unit.objects.create(name="Lourdes", paying_company=company, is_default=True)
        cls.sector = Sector.objects.create(name="Apl. de Provas", is_default=True)
        TaxSettings.objects.create(inss_rate=Decimal("11"), iss_rate=Decimal("5"), ir_rate=Decimal("0"))
        cls.applicator = Applicator.objects.create(full_name="Maria Wolff Florencio")
        cls.user = get_user_model().objects.create_user("rh", password="x")
        cls.user.groups.add(Group.objects.create(name="Gestor financeiro"))
        for shift, amount in ((Shift.MORNING, "93.00"), (Shift.AFTERNOON, "84.00")):
            ServiceEntry.objects.create(
                applicator=cls.applicator, role=ServiceRole.APPLICATOR, activity_date=date(2026, 5, 5),
                event_name="Oficina de Redação", shift=shift, sector=cls.sector, unit=cls.unit,
                net_amount=Decimal(amount),
            )

    def setUp(self):
        self.client.force_login(self.user)

    def _listing(self) -> str:
        response = self.client.get(reverse("payroll:entry_list"))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_the_column_sits_between_date_and_unit(self):
        html = self._listing()
        headers = re.findall(r'<th[^>]*scope="col"[^>]*>(.*?)</th>', html, flags=re.S)
        headers = [re.sub(r"<[^>]+>", "", header).strip() for header in headers]
        self.assertIn("Turno", headers)
        self.assertEqual(headers[headers.index("Data") + 1], "Turno")
        self.assertEqual(headers[headers.index("Turno") + 1], "Unidade")

    def test_both_shifts_of_the_same_day_are_told_apart(self):
        html = self._listing()
        self.assertIn("Manhã", html)
        self.assertIn("Tarde", html)

    def test_an_entry_without_a_shift_does_not_break_the_row(self):
        ServiceEntry.objects.create(
            applicator=self.applicator, role=ServiceRole.APPLICATOR, activity_date=date(2026, 5, 6),
            event_name="Organização de Simulados", shift="", sector=self.sector, unit=self.unit,
            net_amount=Decimal("74.00"),
        )
        self.assertIn("turno não informado", self._listing())