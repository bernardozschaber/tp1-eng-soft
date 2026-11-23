"""A importação não repete um serviço que já está lançado.

O caso real que gerou estes testes: a operação monta a lista da semana copiando
a da semana anterior, e alguma aba fica com a data antiga. As planilhas de
14/09 e 15/09 de 2026 ainda traziam, nas abas de oficina, "08 de Setembro de
2026" — as mesmas pessoas, o mesmo turno, os mesmos valores da planilha de
08/09. Importadas em sequência, cada uma lançava tudo de novo e o resumo pagava
a mesma oficina duas e três vezes.

As planilhas de onde o caso saiu não entram no repositório: são listas de
pagamento reais, com nome e valor de gente de verdade. `SAMPLE_FILES` reconstrói
a mesma pasta — o mesmo layout "Relatório de Atividade", a mesma sequência de
listas e as mesmas abas com data velha — com nomes inventados, montada em
memória a cada teste. O que os testes verificam é a regra, e a regra não depende
de quais pessoas estavam na lista.
"""
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook

from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.imports.services import all_questions, confirm_import, enrich_preview, load_preview, stage_uploads
from apps.imports.views import _cell_text, _is_noise_cell
from apps.payroll.models import ServiceEntry

OFICINAS_08_09 = "08-09 Reaplicação e Oficinas.xlsx"
OFICINAS_14_09 = "14-09 Reaplicação e Simulados.xlsx"

NAMES = [
    "Alice Ferreira Duarte", "Bruno Castro Lima", "Camila Rocha Nunes",
    "Diego Almeida Prado", "Elisa Moura Tavares", "Felipe Gomes Barbosa",
    "Gabriela Santos Reis", "Henrique Vieira Lopes", "Igor Martins Costa",
    "Julia Pereira Mendes", "Karina Bastos Freitas", "Lucas Andrade Pinto",
    "Marina Coelho Ramos", "Nelson Batista Teles", "Olivia Cardoso Braga",
    "Pedro Henrique Sales", "Renata Lima Figueiredo", "Sergio Antunes Mota",
]

OFICINA = "Oficina de Redação"
DATE_08_09, DATE_14_09, DATE_15_09, DATE_01_09 = (
    "08 de Setembro de 2026", "14 de Setembro de 2026",
    "15 de Setembro de 2026", "01 de Setembro de 2026",
)

# As abas de oficina de 08/09: são elas que reaparecem, idênticas, nas listas das
# semanas seguintes — o erro de digitação que os testes reproduzem.
OFICINA_MANHA_08_09 = ("OFICINA MANHÃ", OFICINA, DATE_08_09, "Manhã", NAMES[:10])
OFICINA_TARDE_08_09 = ("OFICINA TARDE", OFICINA, DATE_08_09, "Tarde", NAMES[4:14])

# {nome do arquivo: [(aba, evento, data, turno, pessoas)]}, na ordem em que a
# operação envia as listas.
SAMPLE_FILES = {
    "01-09 Oficinas.xlsx": [
        ("OFICINA MANHÃ", OFICINA, DATE_01_09, "Manhã", NAMES[:14]),
        ("OFICINA TARDE", OFICINA, DATE_01_09, "Tarde", NAMES[4:18]),
    ],
    OFICINAS_08_09: [
        ("REAPLICAÇÃO", "Reaplicação de Provas", DATE_08_09, "Manhã", NAMES[2:16]),
        OFICINA_MANHA_08_09,
        OFICINA_TARDE_08_09,
    ],
    OFICINAS_14_09: [
        ("SIMULADO", "Simulado ENEM", DATE_14_09, "Manhã", NAMES[:14]),
        OFICINA_MANHA_08_09,  # a aba que ficou com a data da semana anterior
        ("REAPLICAÇÃO", "Reaplicação de Provas", DATE_14_09, "Tarde", NAMES[4:16]),
    ],
    "15-09 PBB.xlsx": [
        ("PBB", "Prova Bernoulli Bolsas", DATE_15_09, "Manhã", NAMES),
        OFICINA_TARDE_08_09,  # idem, na lista do dia seguinte
    ],
}


def write_sheet(sheet, event_name, date_text, shift, names) -> None:
    """Uma aba no layout "Relatório de Atividade", como o parser a espera."""
    sheet["D1"] = "Relatório de Atividade"
    sheet["D2"], sheet["F2"], sheet["G2"], sheet["H2"] = "Segmento da Atividade:", event_name, "Data:", date_text
    sheet["D3"], sheet["F3"], sheet["I3"] = "Empresa:", "Matriz", f"Horário: {shift}"
    sheet["D4"], sheet["F4"], sheet["G4"], sheet["H4"] = "Nome", "Aplicador", "Orientador (a)", "Valor"
    for index, name in enumerate(names, start=5):
        is_advisor = index == 5  # o primeiro da lista é o orientador do turno
        sheet[f"D{index}"] = name.upper()
        sheet[f"G{index}" if is_advisor else f"F{index}"] = 1
        sheet[f"H{index}"] = 115 if is_advisor else 102
    total_row = 5 + len(names)
    sheet[f"D{total_row + 2}"] = "ASSINATURA DO RESPONSÁVEL PELA CONTRATAÇÃO:"


def build_workbook(sheets) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, event_name, date_text, shift, names in sheets:
        write_sheet(workbook.create_sheet(title), event_name, date_text, shift, names)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class FakeSession(dict):
    """A sessão só precisa guardar e devolver a prévia."""


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="bernoullipay-tests-"))
class ImportDoesNotDuplicateTests(TestCase):
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
            SimpleUploadedFile(name, build_workbook(SAMPLE_FILES[name]),
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

    # -- os testes --------------------------------------------------------

    def test_the_08_09_list_imports_once(self):
        result = self._import(OFICINAS_08_09)
        self.assertGreater(result["entries"], 0)
        self.assertEqual(result["duplicates"], 0)
        self.assertEqual(self._duplicate_count(), 0)

    def test_importing_the_same_file_twice_adds_nothing(self):
        first = self._import(OFICINAS_08_09)
        total = ServiceEntry.objects.count()
        second = self._import(OFICINAS_08_09)
        self.assertEqual(second["entries"], 0)
        self.assertEqual(second["duplicates"], first["entries"])
        self.assertEqual(ServiceEntry.objects.count(), total)
        self.assertEqual(self._duplicate_count(), 0)

    def test_the_stale_tab_of_the_next_week_does_not_pay_08_09_again(self):
        """O caso relatado: as oficinas de 08/09 voltam na lista de 14/09."""
        self._import(OFICINAS_08_09)
        oficinas_08_09 = ServiceEntry.objects.filter(
            activity_date__year=2026, activity_date__month=9, activity_date__day=8,
            event_key="OFICINA DE REDACAO",
        ).count()
        self.assertGreater(oficinas_08_09, 0)

        result = self._import(OFICINAS_14_09)
        self.assertGreater(result["duplicates"], 0)
        self.assertEqual(
            ServiceEntry.objects.filter(
                activity_date__year=2026, activity_date__month=9, activity_date__day=8,
                event_key="OFICINA DE REDACAO",
            ).count(),
            oficinas_08_09,
            "as oficinas de 08/09 foram lançadas de novo pela lista de 14/09",
        )
        self.assertEqual(self._duplicate_count(), 0)

    def test_nobody_is_paid_twice_for_the_same_shift_across_the_whole_folder(self):
        """A pasta inteira, na ordem em que a operação a enviaria."""
        for name in sorted(SAMPLE_FILES):
            self._import(name)
        self.assertEqual(self._duplicate_count(), 0)
        self.assertGreater(ServiceEntry.objects.count(), 100)


class NoiseCellTests(TestCase):
    """O dump da planilha original some com o que é ruído do template, não dado."""

    def test_phone_cpf_pair_is_noise(self):
        self.assertTrue(_is_noise_cell("32922299 / 03788016899"))

    def test_signature_line_is_noise(self):
        self.assertTrue(_is_noise_cell("ASSINATURA DO RESPONSÁVEL PELA CONTRATAÇÃO:"))

    def test_broken_cell_reference_is_noise(self):
        for text in ("!E", "!F", "!G"):
            self.assertTrue(_is_noise_cell(text), text)

    def test_real_data_is_not_noise(self):
        for text in ("Segmento da Atividade:", "Empresa:", "Maria Silva", "Nome"):
            self.assertFalse(_is_noise_cell(text), text)

    def test_cell_text_collapses_internal_whitespace(self):
        padded = "ASSINATURA:" + " " * 40 + "\nOUTRA LINHA"
        self.assertEqual(_cell_text(padded), "ASSINATURA: OUTRA LINHA")