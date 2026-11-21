"""E2E 3: do cadastro do aplicador à planilha de pagamento exportada."""
import re
from io import BytesIO

from openpyxl import load_workbook
from playwright.sync_api import expect

from apps.catalog.models import Sector, Unit
from e2e.conftest import ADMIN, log_in

# Com as alíquotas padrão (INSS 11%, ISS 5%, IR 0%), R$ 84 líquidos vêm de
# R$ 100 brutos no RPA: números redondos para a conta ficar à vista.
NET, GROSS, INSS, ISS = "84,00", "100,00", "11,00", "5,00"


def test_manager_registers_an_applicator_pays_a_service_and_exports_the_run(page, server):
    """O fechamento de uma quinzena, como o gestor financeiro o faz.

    Cadastro (com a recusa de nome repetido, que é o que impede o mesmo
    aplicador de virar dois RPAs), lançamento manual com a data de pagamento
    calculada pela regra do dia 5 / dia 20, o resumo com o bruto e os
    descontos, e o .xlsx baixado — aberto e conferido, não só baixado.
    """
    log_in(page, server, *ADMIN)
    nav = page.locator("nav.app__nav")
    for label in ("Lançamentos", "Importar", "Resumo", "Aplicadores", "Configurações"):
        expect(nav.get_by_role("link", name=label, exact=True)).to_be_visible()

    # Cadastro.
    nav.get_by_role("link", name="Aplicadores", exact=True).click()
    page.get_by_role("link", name="Novo aplicador").click()
    page.locator("[name=full_name]").fill("Carla  Mendes")
    page.get_by_role("button", name="Salvar").click()
    expect(page.get_by_text("Aplicador Carla Mendes cadastrado.")).to_be_visible()

    page.goto(f"{server}/aplicadores/novo/")
    page.locator("[name=full_name]").fill("CÁRLA mendes")
    page.get_by_role("button", name="Salvar").click()
    expect(page.get_by_text("Já existe um aplicador com este nome: Carla Mendes.")).to_be_visible()

    # Lançamento: atividade em 10/09, até o dia 15 -> paga dia 05/10.
    nav.get_by_role("link", name="Lançamentos", exact=True).click()
    page.get_by_role("link", name="Novo", exact=True).click()
    page.locator("[name=applicator]").select_option(label="Carla Mendes")
    page.locator("[name=activity_date]").fill("2026-09-10")
    page.locator("[name=event_name]").fill("Simulado ENEM II")
    page.locator("[name=sector]").select_option(str(Sector.objects.get(name="APL. DE PROVAS").pk))
    page.locator("[name=unit]").select_option(str(Unit.objects.get(name="Lourdes").pk))
    page.locator("[name=net_amount]").fill("84")
    page.get_by_role("button", name="Salvar").click()

    expect(page).to_have_url(re.compile(r"/lancamentos/$"))
    expect(page.get_by_text("Lançamento de Carla Mendes gravado.")).to_be_visible()
    row = page.locator("table tbody tr", has_text="Carla Mendes")
    expect(row).to_contain_text("05/10/2026")
    expect(row).to_contain_text(GROSS)

    # Resumo do fechamento mais recente.
    nav.get_by_role("link", name="Resumo", exact=True).click()
    expect(page.get_by_text("Pagamento 05/10/2026")).to_be_visible()
    row = page.locator("table tbody tr", has_text="Carla Mendes")
    for value in (GROSS, f"−{INSS}", f"−{ISS}", NET):
        expect(row).to_contain_text(value)

    # Exportação: o arquivo que vai para o financeiro.
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Exportar Excel").click()
    download = download_info.value
    assert download.suggested_filename == "BernoulliPay_pgto_2026-10-05.xlsx"

    workbook = load_workbook(BytesIO(open(download.path(), "rb").read()))
    assert workbook.sheetnames == ["LISTAGEM DE SERVIÇOS PRESTADOS", "RESUMO DE PGTO POR APLICADOR"]
    summary_rows = [
        row for row in workbook["RESUMO DE PGTO POR APLICADOR"].iter_rows(values_only=True) if "Carla Mendes" in row
    ]
    assert len(summary_rows) == 1
    _, name, _, gross, inss, iss, ir, net, *_ = summary_rows[0]
    assert (name, gross, inss, iss, ir, net) == ("Carla Mendes", 100, 11, 5, 0, 84)
