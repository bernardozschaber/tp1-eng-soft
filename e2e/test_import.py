"""E2E 2: importar uma lista de pagamento pela tela, do arquivo ao lançamento."""
import re

from playwright.sync_api import expect

from apps.applicators.models import Applicator
from apps.imports.tests import build_workbook
from apps.payroll.models import ServiceEntry
from e2e.conftest import ADMIN, log_in

# Uma aba no layout "Relatório de Atividade": o primeiro nome é o orientador
# do turno (R$ 115), os demais são aplicadores (R$ 102).
LIST = [("MANHÃ", "Simulado ENEM", "15 de Setembro de 2026", "Manhã", ["Ana Souza", "Bruno Lima"])]


def test_operator_imports_a_list_and_the_same_list_again_pays_nobody_twice(page, server, tmp_path):
    """O caminho inteiro que o operador faz toda semana, com o JS da página.

    `upload.js` só libera o envio com arquivo escolhido; `preview.js` segura o
    "Confirmar" até cada nome novo ter resposta. Depois a mesma planilha volta:
    é o defeito da seção 3 do TESTES.md (a lista reenviada pagava de novo),
    agora visto pela tela — a linha chega desmarcada e nada é lançado.
    """
    Applicator.objects.create(full_name="Ana Souza")
    spreadsheet = tmp_path / "15-09 Simulado.xlsx"
    spreadsheet.write_bytes(build_workbook(LIST))
    log_in(page, server, *ADMIN)

    page.goto(f"{server}/importar/")
    send = page.get_by_role("button", name="Pré-visualizar")
    expect(send).to_be_disabled()
    page.locator("#file-input").set_input_files(spreadsheet)
    expect(page.locator("#file-list")).to_contain_text("15-09 Simulado.xlsx")
    expect(send).to_be_enabled()
    # Desistir do arquivo trava o envio de novo: um POST vazio não chega ao servidor.
    page.locator("#file-input").set_input_files([])
    expect(page.locator("#file-list")).to_be_empty()
    expect(send).to_be_disabled()
    page.locator("#file-input").set_input_files(spreadsheet)
    send.click()

    expect(page).to_have_url(re.compile(r"/importar/previa/$"))
    expect(page.get_by_text("1 arquivo · 2 linhas")).to_be_visible()
    expect(page.get_by_text("1 nome para confirmar antes de lançar.")).to_be_visible()

    # Confirmar com pergunta pendente não envia: abre o card da pergunta.
    page.get_by_role("button", name="Confirmar lançamentos").first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Criar um novo cadastro para o usuário a seguir: Bruno Lima?")
    expect(page).to_have_url(re.compile(r"/importar/previa/$"))
    assert ServiceEntry.objects.count() == 0

    # Respondida a última pergunta, o formulário segue sozinho.
    dialog.get_by_role("button", name="Criar cadastro novo").click()
    expect(page).to_have_url(re.compile(r"/lancamentos/$"))
    expect(page.get_by_text("2 lançamento(s) importado(s), 1 cadastro(s) novo(s) criado(s)")).to_be_visible()
    rows = page.locator("table tbody tr")
    expect(rows.filter(has_text="Ana Souza")).to_contain_text("115,00")
    expect(rows.filter(has_text="Bruno Lima")).to_contain_text("102,00")

    # A mesma lista outra vez.
    page.goto(f"{server}/importar/")
    expect(page.locator("#batches-form")).to_contain_text("15-09 Simulado.xlsx")
    page.locator("#file-input").set_input_files(spreadsheet)
    page.get_by_role("button", name="Pré-visualizar").click()

    expect(page.locator("tr.is-duplicate")).to_have_count(2)
    for name in ("Ana Souza", "Bruno Lima"):
        expect(page.get_by_label(f"Incluir {name} (possível duplicata)")).not_to_be_checked()
    page.get_by_role("button", name="Confirmar lançamentos").first.click()

    expect(page).to_have_url(re.compile(r"/lancamentos/$"))
    expect(page.get_by_text("0 lançamento(s) importado(s)")).to_be_visible()
    assert ServiceEntry.objects.count() == 2
