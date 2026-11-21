"""Infraestrutura dos testes E2E: o sistema de verdade, num navegador de verdade.

Cada teste sobe o Django no `live_server` do pytest-django (estáticos
incluídos, então o JS da página roda) e o pilota com o Chromium do
Playwright. O banco é descartável e recriado a cada teste; o `db.sqlite3`
não é tocado.
"""
import os
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

# O Playwright síncrono roda um event loop na thread do teste, e o Django
# recusa o ORM dentro de um loop assíncrono. Aqui não há concorrência: o teste
# prepara o banco, depois o navegador age, um de cada vez.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

ADMIN = ("admin", "admin")  # o superusuário que `manage.py seed` cria


@pytest.fixture
def server(live_server, transactional_db, settings, tmp_path):
    """URL do sistema rodando, com os dados de referência do `manage.py seed`.

    As planilhas importadas vão para uma pasta temporária, não para `media/`.
    """
    settings.MEDIA_ROOT = tmp_path / "media"
    call_command("seed", stdout=StringIO())
    return live_server.url


@pytest.fixture
def make_user(transactional_db):
    """Cria um usuário num cargo (grupo de acesso), como o `seed_team` faria."""

    def make(username: str, password: str, group: str | None = None):
        user = get_user_model().objects.create_user(username, password=password)
        if group:
            user.groups.add(Group.objects.get_or_create(name=group)[0])
        return user

    return make


def log_in(page, server: str, username: str, password: str) -> None:
    """Entra pela tela de login, como o operador entra."""
    page.goto(f"{server}/login/")
    page.get_by_label("Usuário").fill(username)
    page.get_by_label("Senha").fill(password)
    page.get_by_role("button", name="Entrar").click()
