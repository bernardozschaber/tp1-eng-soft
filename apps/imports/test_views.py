"""As telas da importação, pela borda de fora: envio, prévia, confirmação e lotes."""
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook

from apps.catalog.models import PayingCompany, Sector, Unit
from apps.imports.services import SESSION_KEY, all_questions, load_preview
from apps.imports.tests import build_workbook
from apps.payroll.models import ImportBatch, ServiceEntry

LIST = [("MANHÃ", "Simulado ENEM", "15 de Setembro de 2026", "Manhã", ["Ana Souza", "Bruno Lima"])]


def messages_of(response) -> list[str]:
    return [str(message) for message in response.context["messages"]]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bernoullipay-import-views-"))
class ImportViewsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin", password="admin"))
        company = PayingCompany.objects.create(name="RRPM Matriz")
        self.unit = Unit.objects.create(name="Lourdes", paying_company=company, is_default=True)
        self.sector = Sector.objects.create(name="APL. DE PROVAS", is_default=True)

    def upload(self, *files, follow=False):
        return self.client.post("/importar/", {"files": list(files)}, follow=follow)

    def xlsx(self, name="15-09 Simulado.xlsx", sheets=LIST):
        return SimpleUploadedFile(name, build_workbook(sheets))

    def confirm_payload(self, **fields) -> dict:
        """O POST da prévia com tudo marcado e toda pergunta respondida com "sim"."""
        workbooks = load_preview(self.client.session)
        data = {question["id"]: "sim" for question in all_questions(workbooks)}
        for item in workbooks[0]["sheets"]:
            prefix = "sheet-0-0"
            data.update({
                f"{prefix}-include": "on", f"{prefix}-event_name": item["event_name"],
                f"{prefix}-activity_date": item["activity_date"], f"{prefix}-shift": item["shift"],
                f"{prefix}-unit": self.unit.pk, f"{prefix}-sector": self.sector.pk,
            })
            for index, _ in enumerate(item["rows"]):
                data[f"{prefix}-row-{index}-include"] = "on"
        data.update(fields)
        return data

    # --- envio e prévia ---------------------------------------------------

    def test_upload_without_spreadsheets_is_refused(self):
        response = self.upload(SimpleUploadedFile("notas.pdf", b"%PDF"), follow=True)

        self.assertIn("Selecione ao menos um arquivo .xlsx ou .xlsm.", messages_of(response))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_upload_reports_the_broken_file_and_previews_the_good_one(self):
        response = self.upload(SimpleUploadedFile("ruim.xlsx", b"x"), self.xlsx(), follow=True)

        self.assertRedirects(response, "/importar/previa/")
        self.assertTrue(any(message.startswith("ruim.xlsx:") for message in messages_of(response)))
        self.assertEqual(response.context["total_rows"], 2)
        self.assertEqual(response.context["default_unit"], self.unit)
        self.assertEqual([q["kind"] for q in response.context["questions"]], ["create", "create"])

    def test_preview_and_confirm_without_a_preview_go_back_to_upload(self):
        self.assertRedirects(self.client.get("/importar/previa/"), "/importar/")
        self.assertRedirects(self.client.post("/importar/confirmar/"), "/importar/")

    def test_discard_drops_the_preview(self):
        self.upload(self.xlsx())

        self.assertRedirects(self.client.post("/importar/descartar/"), "/importar/")
        self.assertNotIn(SESSION_KEY, self.client.session)

    # --- confirmação ---------------------------------------------------------

    def test_confirm_posts_the_entries_and_says_what_happened(self):
        self.upload(self.xlsx())

        response = self.client.post("/importar/confirmar/", self.confirm_payload(**{"sheet-0-0-row-1-include": ""}), follow=True)

        self.assertRedirects(response, "/lancamentos/")
        self.assertEqual(ServiceEntry.objects.count(), 1)
        self.assertIn(
            "1 lançamento(s) importado(s), 1 cadastro(s) novo(s) criado(s) (primeiro pagamento), 1 linha(s) ignorada(s).",
            messages_of(response),
        )
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_reimporting_warns_about_the_rows_already_posted(self):
        self.upload(self.xlsx())
        self.client.post("/importar/confirmar/", self.confirm_payload())
        self.upload(self.xlsx())

        response = self.client.post("/importar/confirmar/", self.confirm_payload(), follow=True)

        self.assertEqual(ServiceEntry.objects.count(), 2)
        self.assertTrue(any("2 linha(s) já estavam lançadas" in message for message in messages_of(response)))

    def test_confirm_error_returns_to_the_preview_with_the_reason(self):
        self.upload(self.xlsx())

        response = self.client.post("/importar/confirmar/", self.confirm_payload(**{"sheet-0-0-event_name": ""}), follow=True)

        self.assertRedirects(response, "/importar/previa/")
        self.assertTrue(any("informe nome da atividade e data" in message for message in messages_of(response)))
        self.assertFalse(ServiceEntry.objects.exists())

    # --- lotes -----------------------------------------------------------------

    def imported_batch(self) -> ImportBatch:
        self.upload(self.xlsx())
        self.client.post("/importar/confirmar/", self.confirm_payload())
        return ImportBatch.objects.order_by("-pk").first()

    def test_upload_page_lists_recent_batches_with_totals(self):
        self.imported_batch()

        [batch] = self.client.get("/importar/").context["recent_batches"]

        self.assertEqual((batch.entry_count, batch.net_total, batch.unit_codes), (2, Decimal("217"), ["LOURDES"]))

    def test_batch_preview_shows_the_original_without_template_noise(self):
        batch = self.imported_batch()

        response = self.client.get(f"/importar/lote/{batch.pk}/")

        [sheet] = response.context["sheets"]
        cells = [cell for row in sheet["rows"] for cell in row]
        self.assertIn("ANA SOUZA", cells)
        self.assertFalse(any(cell.startswith("ASSINATURA") for cell in cells))
        self.assertFalse(sheet["truncated"])

    def test_batch_preview_truncates_long_sheets(self):
        workbook = Workbook()
        for number in range(250):
            workbook.active.append([f"linha {number}"])
        buffer = BytesIO()
        workbook.save(buffer)
        batch = ImportBatch.objects.create(file_name="longa.xlsx")
        batch.source_file.save("longa.xlsx", ContentFile(buffer.getvalue()))

        [sheet] = self.client.get(f"/importar/lote/{batch.pk}/").context["sheets"]

        self.assertTrue(sheet["truncated"])
        self.assertEqual(len(sheet["rows"]), 200)

    def test_batch_without_original_or_with_missing_file(self):
        old = ImportBatch.objects.create(file_name="antiga.xlsx")
        response = self.client.get(f"/importar/lote/{old.pk}/", follow=True)
        self.assertTrue(any("anterior ao arquivamento" in message for message in messages_of(response)))
        self.assertEqual(self.client.get(f"/importar/lote/{old.pk}/arquivo/").status_code, 404)

        gone = self.imported_batch()
        gone.source_file.storage.delete(gone.source_file.name)
        response = self.client.get(f"/importar/lote/{gone.pk}/", follow=True)
        self.assertTrue(any("não está mais no servidor" in message for message in messages_of(response)))

    def test_download_returns_the_original_under_its_name(self):
        batch = self.imported_batch()

        response = self.client.get(f"/importar/lote/{batch.pk}/arquivo/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('filename="15-09 Simulado.xlsx"', response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"PK"))

    def test_deleting_a_batch_takes_its_entries_and_file(self):
        batch = self.imported_batch()
        storage, name = batch.source_file.storage, batch.source_file.name

        response = self.client.post(f"/importar/lote/{batch.pk}/excluir/", follow=True)

        self.assertFalse(ServiceEntry.objects.exists())
        self.assertFalse(storage.exists(name))
        self.assertIn("Importação “15-09 Simulado.xlsx” removida: 2 lançamento(s) excluído(s).", messages_of(response))

    def test_bulk_delete_ignores_tampered_ids_and_needs_a_selection(self):
        batch = self.imported_batch()

        response = self.client.post("/importar/lotes/excluir/", {"batches": ["1 OR 1=1", "abc"]}, follow=True)
        self.assertIn("Selecione ao menos uma importação para excluir.", messages_of(response))
        self.assertTrue(ImportBatch.objects.exists())

        response = self.client.post("/importar/lotes/excluir/", {"batches": [str(batch.pk), "x"]}, follow=True)
        self.assertIn("1 importação(ões) removida(s): 2 lançamento(s) excluído(s).", messages_of(response))
        self.assertFalse(ImportBatch.objects.exists())
