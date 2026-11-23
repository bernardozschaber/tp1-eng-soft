"""As telas da importação, pela borda de fora: envio, prévia, confirmação e lotes."""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.catalog.models import PayingCompany, Sector, Unit
from apps.imports.services import SESSION_KEY
from apps.imports.tests import build_workbook

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