"""Item 6 do roteiro de TESTES.md: cada filtro isolado e combinado.

Filtro errado mostra um fechamento incompleto sem avisar ninguém, então cada
um tem um caso que só ele separa.
"""
from datetime import date

from django.http import QueryDict
from django.test import TestCase

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.payroll.filters import EntryFilters
from apps.payroll.models import ServiceEntry, ServiceRole, Shift


def filters(query: str) -> EntryFilters:
    return EntryFilters.from_request(QueryDict(query))


class EntryFiltersParsingTests(TestCase):
    def test_empty_request_filters_nothing(self):
        parsed = filters("")

        self.assertEqual((parsed.query, parsed.unit_id, parsed.payment_date), ("", None, None))
        self.assertFalse(parsed.inconsistent_only)

    def test_bad_numbers_and_dates_are_ignored_not_errors(self):
        parsed = filters("unit=abc&sector=-1&payment_date=2026-13-40&from=ontem")

        self.assertIsNone(parsed.unit_id)
        self.assertIsNone(parsed.sector_id)
        self.assertIsNone(parsed.payment_date)
        self.assertIsNone(parsed.date_from)

    def test_inconsistent_flag(self):
        self.assertTrue(filters("inconsistent=1").inconsistent_only)
        self.assertFalse(filters("inconsistent=0").inconsistent_only)

    def test_querystring_keeps_filters_but_drops_the_page(self):
        self.assertEqual(filters("q=ana&unit=2&page=3").querystring(), "q=ana&unit=2")


class EntryFiltersApplyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = PayingCompany.objects.create(name="RRPM A")
        cls.company_b = PayingCompany.objects.create(name="RRPM B")
        cls.unit_a = Unit.objects.create(name="Lourdes Teste", paying_company=cls.company_a)
        cls.unit_b = Unit.objects.create(name="Sereno Teste", paying_company=cls.company_b)
        cls.sector_a = Sector.objects.create(name="SETOR A")
        cls.sector_b = Sector.objects.create(name="SETOR B")
        cls.ana = Applicator.objects.create(full_name="Ana Souza")
        cls.bruno = Applicator.objects.create(full_name="Bruno Lima")

        def entry(applicator, day, unit, sector, event="Simulado", notes=""):
            return ServiceEntry.objects.create(
                applicator=applicator, role=ServiceRole.APPLICATOR, activity_date=day, event_name=event,
                shift=Shift.MORNING, sector=sector, unit=unit, net_amount=100, notes=notes,
            )

        cls.early = entry(cls.ana, date(2026, 9, 2), cls.unit_a, cls.sector_a, event="Prova Regular")
        cls.late = entry(cls.bruno, date(2026, 9, 20), cls.unit_b, cls.sector_b, notes="reposição")
        cls.ana_late = entry(cls.ana, date(2026, 9, 21), cls.unit_b, cls.sector_a)

    def pks(self, query: str) -> set[int]:
        return set(filters(query).apply().values_list("pk", flat=True))

    def test_no_filter_returns_everything(self):
        self.assertEqual(self.pks(""), {self.early.pk, self.late.pk, self.ana_late.pk})

    def test_text_search_covers_name_event_unit_and_notes(self):
        self.assertEqual(self.pks("q=bruno"), {self.late.pk})
        self.assertEqual(self.pks("q=prova regular"), {self.early.pk})
        self.assertEqual(self.pks("q=lourdes"), {self.early.pk})
        self.assertEqual(self.pks("q=reposi"), {self.late.pk})

    def test_each_id_filter_alone(self):
        self.assertEqual(self.pks(f"unit={self.unit_a.pk}"), {self.early.pk})
        self.assertEqual(self.pks(f"company={self.company_b.pk}"), {self.late.pk, self.ana_late.pk})
        self.assertEqual(self.pks(f"sector={self.sector_b.pk}"), {self.late.pk})
        self.assertEqual(self.pks(f"applicator={self.ana.pk}"), {self.early.pk, self.ana_late.pk})

    def test_activity_date_range_is_inclusive(self):
        self.assertEqual(self.pks("from=2026-09-20"), {self.late.pk, self.ana_late.pk})
        self.assertEqual(self.pks("to=2026-09-20"), {self.early.pk, self.late.pk})
        self.assertEqual(self.pks("from=2026-09-20&to=2026-09-20"), {self.late.pk})

    def test_payment_date(self):
        self.assertEqual(self.pks(f"payment_date={self.early.payment_date:%Y-%m-%d}"), {self.early.pk})

    def test_filters_combine_with_and(self):
        self.assertEqual(self.pks(f"applicator={self.ana.pk}&unit={self.unit_b.pk}"), {self.ana_late.pk})
        self.assertEqual(self.pks(f"applicator={self.bruno.pk}&sector={self.sector_a.pk}"), set())

    def test_scope_defaults_to_the_latest_payment_run(self):
        scoped = filters("").scope_to_payment_run()

        self.assertTrue(scoped.payment_date_defaulted)
        self.assertEqual(scoped.payment_date, max(e.payment_date for e in (self.early, self.late, self.ana_late)))

    def test_scope_on_an_empty_database_stays_empty(self):
        ServiceEntry.objects.all().delete()

        scoped = filters("").scope_to_payment_run()

        self.assertIsNone(scoped.payment_date)
        self.assertFalse(scoped.payment_date_defaulted)
