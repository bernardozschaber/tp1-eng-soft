"""Item 4 do roteiro de TESTES.md: as perguntas da prévia e a confirmação.

`merge_questions` e `creation_questions` decidem se duas grafias são uma
pessoa ou duas; errar paga em dobro por outro caminho. Os testes montam a
prévia direto no formato JSON que a sessão guarda, sem passar por planilha:
o parser tem os próprios testes em `test_parser.py`.
"""
import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.applicators.models import Applicator, RegistrationStatus
from apps.catalog.models import PayingCompany, Sector, Unit
from apps.imports.services import (
    SESSION_KEY,
    _amount_from,
    _follow_chains,
    _short_date,
    all_questions,
    confirm_import,
    creation_questions,
    enrich_preview,
    merge_questions,
    read_answers,
    stage_uploads,
)
from apps.imports.tests import build_workbook
from apps.payroll.models import ImportBatch, ServiceEntry, ServiceRole, Shift

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


class ReadAnswersTests(TestCase):
    def setUp(self):
        self.workbooks = preview(sheet(row("LARISSA MAIA"), row("LARISSA SALGADO MAIA"), row("CAMILA NUNES")))
        self.merge_id = merge_questions(self.workbooks)[0]["id"]
        self.create_id = creation_questions(self.workbooks)[0]["id"]

    def test_unanswered_merge_stops_the_import(self):
        with self.assertRaisesMessage(ValueError, "nomes parecidos"):
            read_answers({self.create_id: "sim"}, self.workbooks)

    def test_unanswered_creation_stops_the_import(self):
        with self.assertRaisesMessage(ValueError, "cadastros novos"):
            read_answers({self.merge_id: "nao"}, self.workbooks)

    def test_declined_creation_and_confirmed_merge(self):
        merges, declined = read_answers({self.merge_id: "sim", self.create_id: "nao"}, self.workbooks)

        self.assertEqual(merges, {"LARISSA MAIA": "name:Larissa Salgado Maia"})
        self.assertEqual(declined, {"CAMILA NUNES"})

    def test_answer_pointing_to_a_deleted_record_stops_the_import(self):
        for answer in ("applicator:999", "applicator:abc"):
            with self.subTest(answer=answer), self.assertRaisesMessage(ValueError, "não existe mais"):
                read_answers({self.merge_id: "nao", self.create_id: answer}, self.workbooks)


# --- confirmação -------------------------------------------------------------


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bernoullipay-services-"))
class ConfirmImportTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        company = PayingCompany.objects.create(name="RRPM Matriz")
        self.unit = Unit.objects.create(name="Lourdes", paying_company=company)
        self.sector = Sector.objects.create(name="APL. DE PROVAS")
        self.user = get_user_model().objects.create_user("rh")

    def payload(self, workbooks, answers=None, **fields):
        """O POST da prévia com tudo marcado; `fields` sobrescreve campo a campo."""
        data = {}
        for file_index, workbook in enumerate(workbooks):
            for sheet_index, item in enumerate(workbook["sheets"]):
                prefix = f"sheet-{file_index}-{sheet_index}"
                data.update({
                    f"{prefix}-include": "on", f"{prefix}-event_name": item["event_name"],
                    f"{prefix}-activity_date": item["activity_date"], f"{prefix}-shift": item["shift"],
                    f"{prefix}-unit": str(self.unit.pk), f"{prefix}-sector": str(self.sector.pk),
                })
                for row_index, _ in enumerate(item["rows"]):
                    data[f"{prefix}-row-{row_index}-include"] = "on"
        for question in all_questions(workbooks):
            data[question["id"]] = (answers or {}).get(question["variant"]["normalized"], "sim")
        data.update(fields)
        return data

    def confirm(self, workbooks, answers=None, **fields):
        return confirm_import(self.payload(workbooks, answers, **fields), workbooks, self.user)

    def test_confirmed_merge_puts_both_spellings_on_one_record(self):
        workbooks = preview(
            sheet(row("LARISSA MAIA")),
            sheet(row("LARISSA SALGADO MAIA"), name="TARDE", shift="TARDE"),
        )

        result = self.confirm(workbooks)

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Larissa Salgado Maia"])
        self.assertEqual((result["entries"], result["merged"], result["applicators"]), (2, 1, 1))

    def test_merge_into_an_existing_record_creates_nobody(self):
        larissa = Applicator.objects.create(full_name="Larissa Salgado Maia")

        result = self.confirm(preview(sheet(row("LARISSA MAIA"))))

        self.assertEqual(result["applicators"], 0)
        self.assertEqual(ServiceEntry.objects.get().applicator, larissa)

    def test_declined_creation_leaves_the_rows_out(self):
        result = self.confirm(preview(sheet(row("CAMILA NUNES"), row("BRUNO LIMA"))), {"CAMILA NUNES": "nao"})

        self.assertEqual(list(Applicator.objects.values_list("full_name", flat=True)), ["Bruno Lima"])
        self.assertEqual(result["skipped"], 1)

    def test_creation_answered_with_another_record_posts_there(self):
        bruno = Applicator.objects.create(full_name="Bruno Lima")

        self.confirm(preview(sheet(row("CAMILA NUNES"))), {"CAMILA NUNES": f"applicator:{bruno.pk}"})

        self.assertEqual(ServiceEntry.objects.get().applicator, bruno)
        self.assertEqual(Applicator.objects.count(), 1)

    def test_new_applicator_is_first_payment_and_keeps_the_suffix(self):
        self.confirm(preview(sheet(row("MARIA SILVA (C.E. ONLINE)"))))

        maria = Applicator.objects.get()
        self.assertEqual((maria.full_name, maria.registration_status), ("Maria Silva", RegistrationStatus.NEW))
        self.assertIn("Sufixo na lista: C.E. ONLINE", maria.notes)
        self.assertEqual(ServiceEntry.objects.get().notes, "C.E. ONLINE")

    def test_cpf_matches_a_record_written_another_way_and_fills_a_missing_cpf(self):
        # "A. Prado" não se parece com "Ana Souza Prado" para a heurística de
        # nomes; quem casa os dois é só o CPF.
        ana = Applicator.objects.create(full_name="Ana Souza Prado", cpf="529.982.247-25")
        bruno = Applicator.objects.create(full_name="Bruno Lima")
        workbooks = preview(sheet(row("A. PRADO", cpf="52998224725"), row("BRUNO LIMA", cpf="111.444.777-35")))

        self.confirm(workbooks)

        self.assertEqual(set(ServiceEntry.objects.values_list("applicator", flat=True)), {ana.pk, bruno.pk})
        bruno.refresh_from_db()
        self.assertEqual(bruno.cpf, "111.444.777-35")

    def test_forms_list_uses_the_amount_typed_for_the_sheet(self):
        workbooks = preview(sheet(row("BRUNO LIMA", amount="0")))

        self.confirm(workbooks, **{"sheet-0-0-default_amount": "85,50"})

        self.assertEqual(ServiceEntry.objects.get().net_amount, Decimal("85.50"))

    def test_forms_list_without_any_amount_is_refused(self):
        with self.assertRaisesMessage(ValueError, "informe o valor por pessoa"):
            self.confirm(preview(sheet(row("BRUNO LIMA", amount="0"))))

        self.assertFalse(ServiceEntry.objects.exists())

    def test_sheet_without_event_or_date_is_refused(self):
        with self.assertRaisesMessage(ValueError, "informe nome da atividade e data"):
            self.confirm(preview(sheet(row("BRUNO LIMA"), day="")))

    def test_unchecked_sheet_and_row_and_unknown_role(self):
        workbooks = preview(sheet(row("BRUNO LIMA"), row("CAMILA NUNES")), sheet(row("DIEGO PRADO"), name="OUTRA"))

        result = self.confirm(
            workbooks, **{"sheet-0-1-include": "", "sheet-0-0-row-1-include": "", "sheet-0-0-row-0-role": "CHEFE"}
        )

        entry = ServiceEntry.objects.get()
        self.assertEqual((entry.applicator.full_name, entry.role), ("Bruno Lima", ServiceRole.APPLICATOR))
        self.assertEqual(result["skipped"], 1)

    def test_batch_keeps_the_spreadsheet_under_its_original_name(self):
        staged = default_storage.save("imports/_staging/abc.xlsx", ContentFile(b"planilha"))

        self.confirm(preview(sheet(row("BRUNO LIMA")), file_name="08-09 Oficinas.xlsx", staged_path=staged))

        # O storage troca espaço por "_", mas o nome é o que a operação enviou.
        self.assertTrue(ImportBatch.objects.get().source_file.name.endswith("08-09_Oficinas.xlsx"))
        self.assertFalse(default_storage.exists(staged))

    def test_all_duplicates_leave_no_empty_batch_and_drop_the_staged_file(self):
        self.confirm(preview(sheet(row("BRUNO LIMA"))))
        staged = default_storage.save("imports/_staging/again.xlsx", ContentFile(b"planilha"))

        result = self.confirm(preview(sheet(row("BRUNO LIMA")), staged_path=staged))

        self.assertEqual((result["entries"], result["duplicates"]), (0, 1))
        self.assertEqual(ImportBatch.objects.count(), 1)
        self.assertFalse(default_storage.exists(staged))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bernoullipay-staging-"))
class StageUploadsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def upload(self, name, content):
        return SimpleUploadedFile(name, content)

    def test_unreadable_file_is_reported_and_the_rest_is_staged(self):
        good = build_workbook([("MANHÃ", "Simulado", "15 de Setembro de 2026", "Manhã", ["Ana Souza"])])
        session = {}

        errors = stage_uploads(session, [self.upload("ruim.xlsx", b"nao e planilha"), self.upload("boa.xlsx", good)])

        self.assertEqual([error["file_name"] for error in errors], ["ruim.xlsx"])
        [workbook] = session[SESSION_KEY]
        self.assertEqual((workbook["file_name"], workbook["row_count"]), ("boa.xlsx", 1))
        self.assertEqual(workbook["sheets"][0]["activity_date"], DAY)
        self.assertTrue(default_storage.exists(workbook["staged_path"]))

    def test_a_new_preview_deletes_the_files_of_the_previous_one(self):
        content = build_workbook([("MANHÃ", "Simulado", "15 de Setembro de 2026", "Manhã", ["Ana Souza"])])
        session = {}
        stage_uploads(session, [self.upload("primeira.xlsx", content)])
        first = session[SESSION_KEY][0]["staged_path"]

        stage_uploads(session, [self.upload("segunda.xlsx", content)])

        self.assertFalse(default_storage.exists(first))
        self.assertEqual(session[SESSION_KEY][0]["file_name"], "segunda.xlsx")
