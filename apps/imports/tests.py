"""A importação não repete um serviço que já está lançado.

O caso real que gerou estes testes: a operação monta a lista da semana copiando
a da semana anterior, e alguma aba fica com a data antiga. As planilhas de
14/09 e 15/09 de 2026 ainda trazem, nas abas de oficina, "08 de Setembro de
2026" — as mesmas pessoas, o mesmo turno, os mesmos valores da planilha de
08/09. Importadas em sequência, cada uma lançava tudo de novo e o resumo pagava
a mesma oficina duas e três vezes.

Os testes rodam sobre os arquivos de verdade, em `01-09 oficina e pbb/`.
"""
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.imports.services import all_questions, confirm_import, enrich_preview, load_preview, stage_uploads
from apps.payroll.models import ServiceEntry

SAMPLES = Path(__file__).resolve().parents[2] / "01-09 oficina e pbb"
OFICINAS_08_09 = "08-09 Reaplicação e Oficinas.xlsx"
OFICINAS_14_09 = "14-09 Reaplicação e Simulados.xlsx"


class FakeSession(dict):
    """A sessão só precisa guardar e devolver a prévia."""


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bernoullipay-tests-"))
class ImportDoesNotDuplicateTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not SAMPLES.is_dir():
            raise cls.failureException(f"planilhas de exemplo não encontradas em {SAMPLES}")

    @classmethod
    def tearDownClass(cls):
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        company = PayingCompany.objects.create(name="RRPM Matriz")
        self.unit = Unit.objects.create(name="Lourdes", paying_company=company, is_default=True)
        self.sector = Sector.objects.create(name="Apl. de Provas", is_default=True)
        TaxSettings.objects.create(inss_rate=Decimal("11"), iss_rate=Decimal("5"), ir_rate=Decimal("0"))
        self.user = get_user_model().objects.create_user("rh", password="x")
        self.session = FakeSession()

    # -- ajudantes --------------------------------------------------------

    def _payload(self, workbooks) -> dict:
        """Monta o POST que a tela de prévia enviaria com tudo marcado.

        Toda pergunta de criação vira "sim" (é gente nova, o banco está vazio) e
        toda pergunta de junção vira "não", para que nenhum nome parecido se
        funda sozinho e os testes falem só de serviços repetidos.
        """
        payload = {}
        for sheet in (sheet for workbook in workbooks for sheet in workbook["sheets"]):
            payload[f"{sheet['prefix']}-include"] = "on"
            payload[f"{sheet['prefix']}-event_name"] = sheet["event_name"]
            payload[f"{sheet['prefix']}-activity_date"] = sheet["activity_date"]
            payload[f"{sheet['prefix']}-shift"] = sheet["shift"]
            payload[f"{sheet['prefix']}-unit"] = str(self.unit.pk)
            payload[f"{sheet['prefix']}-sector"] = str(self.sector.pk)
            payload[f"{sheet['prefix']}-default_amount"] = ""
            for row in sheet["rows"]:
                payload[f"{row['prefix']}-include"] = "on"
                payload[f"{row['prefix']}-net_amount"] = row["net_amount"]
                payload[f"{row['prefix']}-role"] = row["role"]
        for question in all_questions(workbooks):
            payload[question["id"]] = "sim" if question["kind"] == "create" else "nao"
        return payload

    def _import(self, *file_names) -> dict:
        uploads = [
            SimpleUploadedFile(name, (SAMPLES / name).read_bytes(),
                               content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            for name in file_names
        ]
        self.assertEqual(stage_uploads(self.session, uploads), [])
        workbooks = enrich_preview(load_preview(self.session))
        return confirm_import(self._payload(workbooks), workbooks, self.user)

    def _duplicate_count(self) -> int:
        from django.db.models import Count

        return (
            ServiceEntry.objects.values(*ServiceEntry.IDENTITY_FIELDS)
            .annotate(n=Count("id")).filter(n__gt=1).count()
        )