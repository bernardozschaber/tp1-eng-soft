"""E2E 4: desfazer importações erradas, em lote, sem apagar o que não devia."""
from datetime import date

from playwright.sync_api import expect

from apps.applicators.models import Applicator
from apps.catalog.models import Sector, Unit
from apps.payroll.models import ImportBatch, ServiceEntry
from e2e.conftest import ADMIN, log_in


def import_batch(file_name: str, people: list[str], day: int) -> ImportBatch:
    """Um lote já confirmado, com um lançamento por pessoa."""
    batch = ImportBatch.objects.create(file_name=file_name)
    for name in people:
        ServiceEntry.objects.create(
            applicator=Applicator.objects.get_or_create(full_name=name)[0], activity_date=date(2026, 9, day),
            event_name="Simulado ENEM", sector=Sector.objects.get(is_default=True),
            unit=Unit.objects.get(is_default=True), net_amount=102, import_batch=batch,
        )
    return batch


def test_operator_deletes_two_of_three_imports_after_confirming_the_count(page, server):
    """Excluir um lote apaga os pagamentos que ele criou: o número tem de estar à vista.

    O botão só aparece com seleção e diz quantos lançamentos vão junto; o
    "Cancelar" do navegador não pode apagar nada; e a importação que ficou de
    fora da seleção — e os pagamentos dela — continuam lá.
    """
    import_batch("01-09 Oficinas.xlsx", ["Ana Souza", "Bruno Lima"], day=1)
    import_batch("08-09 Oficinas.xlsx", ["Ana Souza"], day=8)
    import_batch("15-09 PBB.xlsx", ["Bruno Lima"], day=15)
    log_in(page, server, *ADMIN)
    page.goto(f"{server}/importar/")

    bulk = page.locator("#bulk-delete")
    select_all = page.get_by_label("Selecionar todas as importações")
    expect(bulk).to_be_hidden()

    page.get_by_label("Selecionar a importação 01-09 Oficinas.xlsx").check()
    expect(bulk).to_have_text("Excluir 1 selecionada · 2 lançamentos")

    select_all.check()
    expect(bulk).to_have_text("Excluir 3 selecionadas · 4 lançamentos")

    page.get_by_label("Selecionar a importação 15-09 PBB.xlsx").uncheck()
    expect(bulk).to_have_text("Excluir 2 selecionadas · 3 lançamentos")
    assert select_all.evaluate("box => box.indeterminate")

    # Primeiro o operador desiste no confirm() do navegador.
    questions = []

    def answer(dialog, accept: bool):
        questions.append(dialog.message)
        dialog.accept() if accept else dialog.dismiss()

    page.once("dialog", lambda dialog: answer(dialog, accept=False))
    bulk.click()
    expect(bulk).to_be_visible()
    assert ImportBatch.objects.count() == 3

    page.once("dialog", lambda dialog: answer(dialog, accept=True))
    bulk.click()
    expect(page.get_by_text("2 importação(ões) removida(s): 3 lançamento(s) excluído(s).")).to_be_visible()

    assert questions == ["Excluir 2 importação(ões) e os 3 lançamento(s) que elas criaram?"] * 2
    table = page.locator("#batches-form tbody")
    expect(table.locator("tr")).to_have_count(1)
    expect(table).to_contain_text("15-09 PBB.xlsx")
    assert list(ServiceEntry.objects.values_list("applicator__full_name", "activity_date")) == [
        ("Bruno Lima", date(2026, 9, 15))
    ]
    assert Applicator.objects.count() == 2  # o cadastro fica; só os pagamentos saem
