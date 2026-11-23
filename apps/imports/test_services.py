"""Item 4 do roteiro de TESTES.md: as perguntas da prévia e a confirmação.

`merge_questions` e `creation_questions` decidem se duas grafias são uma
pessoa ou duas; errar paga em dobro por outro caminho. Os testes montam a
prévia direto no formato JSON que a sessão guarda, sem passar por planilha:
o parser tem os próprios testes em `test_parser.py`.
"""
from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from apps.applicators.models import Applicator, RegistrationStatus
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.imports.services import (
    _amount_from,
    _follow_chains,
    _short_date,
    all_questions,
    creation_questions,
    enrich_preview,
    merge_questions,
)
from apps.payroll.models import ServiceEntry, ServiceRole, Shift

DAY = "2026-09-15"


def row(name, amount="102", role="APLICADOR", cpf=""):
    return {"name": name, "role": role, "net_amount": amount, "source_row": 5, "cpf": cpf}


def sheet(*rows, name="MANHÃ", event="Simulado", day=DAY, shift="MANHA"):
    return {"sheet_name": name, "event_name": event, "activity_date": day, "shift": shift, "rows": list(rows)}


def preview(*sheets, file_name="lista.xlsx", staged_path=None):
    return [{"file_name": file_name, "sheets": list(sheets), "staged_path": staged_path}]


# --- funções puras -----------------------------------------------------------


class SmallHelpersTests(SimpleTestCase):
    def test_typed_amounts(self):
        self.assertEqual(_amount_from("85"), Decimal("85"))
        self.assertEqual(_amount_from("R$ 85,50"), Decimal("85.50"))
        self.assertEqual(_amount_from("1.234,5"), Decimal("1234.5"))
        self.assertEqual(_amount_from("", fallback=Decimal("7")), Decimal("7"))
        self.assertEqual(_amount_from("a combinar", fallback=Decimal("7")), Decimal("7"))

    def test_short_date(self):
        self.assertEqual(_short_date("2026-09-15"), "15/09/2026")
        self.assertEqual(_short_date(""), "sem data")
        self.assertEqual(_short_date("15 de setembro"), "15 de setembro")

    def test_chains_end_at_the_last_target(self):
        answers = {
            "FELIPE CARNEIRO": ("FELIPE CARDOSO", "name:Felipe Cardoso"),
            "FELIPE CARDOSO": ("FELIPE CARDOSO OLIVEIRA", "applicator:7"),
        }

        self.assertEqual(
            _follow_chains(answers),
            {"FELIPE CARNEIRO": "applicator:7", "FELIPE CARDOSO": "applicator:7"},
        )

    def test_a_cycle_does_not_loop_forever(self):
        answers = {"ANA A": ("ANA B", "name:Ana B"), "ANA B": ("ANA A", "name:Ana A")}

        self.assertEqual(set(_follow_chains(answers)), {"ANA A", "ANA B"})


# --- perguntas ---------------------------------------------------------------


class QuestionTests(TestCase):
    def test_short_spelling_asks_once_toward_the_fuller_name(self):
        workbooks = preview(
            sheet(row("LARISSA MAIA"), row("LARISSA SALGADO MAIA")),
            sheet(row("LARISSA MAIA"), name="TARDE", shift="TARDE"),
        )

        [question] = merge_questions(workbooks)

        self.assertEqual(question["variant"]["normalized"], "LARISSA MAIA")
        self.assertEqual(question["variant"]["count"], 2)
        self.assertEqual(question["target"]["value"], "name:Larissa Salgado Maia")
        self.assertEqual(creation_questions(workbooks), [])

    def test_similar_registered_applicator_is_offered_with_its_history(self):
        larissa = Applicator.objects.create(full_name="Larissa Salgado Maia", registration_status=RegistrationStatus.ACTIVE)
        company = PayingCompany.objects.create(name="RRPM T")
        ServiceEntry.objects.create(
            applicator=larissa, role=ServiceRole.APPLICATOR, activity_date=date(2026, 9, 1), event_name="Prova",
            shift=Shift.MORNING, sector=Sector.objects.create(name="S"),
            unit=Unit.objects.create(name="U", paying_company=company), net_amount=100,
        )

        [question] = merge_questions(preview(sheet(row("LARISSA MAIA"))))

        self.assertEqual(question["target"]["value"], f"applicator:{larissa.pk}")
        self.assertIn("1 lançamento(s) no sistema", question["target"]["detail"])

    def test_fuller_name_in_the_preview_that_is_registered_points_to_the_record(self):
        larissa = Applicator.objects.create(full_name="Larissa Salgado Maia")

        [question] = merge_questions(preview(sheet(row("LARISSA MAIA"), row("LARISSA SALGADO MAIA"))))

        self.assertEqual(question["target"]["value"], f"applicator:{larissa.pk}")
        self.assertTrue(question["target"]["detail"].startswith("já cadastrado"))

    def test_enrich_marks_known_people_duplicates_and_gross_amount(self):
        bruno = Applicator.objects.create(full_name="Bruno Lima")
        company = PayingCompany.objects.create(name="RRPM T")
        ServiceEntry.objects.create(
            applicator=bruno, role=ServiceRole.APPLICATOR, activity_date=date(2026, 9, 15), event_name="Simulado",
            shift=Shift.MORNING, sector=Sector.objects.create(name="S"),
            unit=Unit.objects.create(name="U", paying_company=company), net_amount=102,
        )

        [workbook] = enrich_preview(preview(sheet(row("BRUNO LIMA"), row("MARIA SILVA (C.E. ONLINE)"))))

        known, new = workbook["sheets"][0]["rows"]
        self.assertEqual((known["prefix"], known["is_known"], known["is_duplicate"]), ("sheet-0-0-row-0", True, True))
        self.assertEqual((new["display_name"], new["suffix"], new["is_known"]), ("Maria Silva", "C.E. ONLINE", False))
        self.assertGreater(Decimal(new["gross_amount"]), Decimal("102"))

    def test_unknown_name_that_resembles_nobody_asks_for_creation(self):
        Applicator.objects.create(full_name="Bruno Lima")

        questions = all_questions(preview(sheet(row("BRUNO LIMA"), row("CAMILA NUNES"))))

        self.assertEqual([(q["kind"], q["variant"]["normalized"]) for q in questions], [("create", "CAMILA NUNES")])