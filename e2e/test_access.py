"""E2E 1: entrar no sistema e enxergar só o que o cargo permite."""
import re

from playwright.sync_api import expect


def test_rh_user_logs_in_and_only_reaches_the_import_area(page, server, make_user):
    """O RH importa listas, mas não vê valores pagos nem cadastro.

    Se o bloqueio fosse só o menu escondido, quem recebesse um link de
    /lancamentos/ veria a folha inteira. O teste segue esse link sem estar
    logado, erra a senha, entra e confere que o servidor barrou a URL — e que
    o menu e a tela de importação continuam ao alcance.
    """
    make_user("felipe.oliveira", "5424", group="Usuário do RH")

    page.goto(f"{server}/lancamentos/")
    expect(page).to_have_url(re.compile(r"/login/\?next=/lancamentos/$"))

    page.get_by_label("Usuário").fill("felipe.oliveira")
    page.get_by_label("Senha").fill("senha-errada")
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_text("Usuário ou senha inválidos.")).to_be_visible()

    page.get_by_label("Usuário").fill("felipe.oliveira")
    page.get_by_label("Senha").fill("5424")
    page.get_by_role("button", name="Entrar").click()

    # O login devolve para /lancamentos/, e o middleware manda de volta ao Início.
    expect(page).to_have_url(f"{server}/")
    expect(page.get_by_text("Seu acesso não inclui esta área.")).to_be_visible()

    nav = page.locator("nav.app__nav")
    expect(nav.get_by_role("link", name="Início", exact=True)).to_be_visible()
    expect(nav.get_by_role("link", name="Importar", exact=True)).to_be_visible()
    for hidden in ("Lançamentos", "Resumo", "Aplicadores", "Configurações"):
        expect(nav.get_by_role("link", name=hidden, exact=True)).to_have_count(0)

    page.goto(f"{server}/configuracoes/")
    expect(page).to_have_url(f"{server}/")

    nav.get_by_role("link", name="Importar", exact=True).click()
    expect(page.get_by_role("heading", name="Importar listas de pagamento")).to_be_visible()

    page.get_by_role("button", name="Sair da conta").click()
    expect(page).to_have_url(re.compile(r"/login/$"))
    page.goto(f"{server}/importar/")
    expect(page).to_have_url(re.compile(r"/login/\?next=/importar/$"))

