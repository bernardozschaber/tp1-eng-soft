"""Item 8 do roteiro de TESTES.md: toda rota exige login, e exclusão exige POST.

Até aqui só o `@login_required` em cada view garantia isso, e nada verificava
que ele continuava lá. Estes testes percorrem o URLconf inteiro, então uma view
nova sem o decorador quebra o teste sem ninguém precisar lembrar de listá-la.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver

# Rotas que são públicas de propósito.
PUBLIC = {"login", "logout"}
# O admin do Django tem a própria barreira, testada pelo próprio Django.
SKIPPED_PREFIXES = ("admin/",)
# Exclusões: um GET num link não pode apagar nada.
POST_ONLY = [
    "/aplicadores/1/excluir/",
    "/lancamentos/1/excluir/",
    "/importar/lote/1/excluir/",
    "/importar/lotes/excluir/",
    "/configuracoes/padrao/unit/1/",
]


def concrete_paths(patterns=None, prefix=""):
    """(nome, caminho) de cada rota, com 1 no lugar de cada parâmetro."""
    for pattern in patterns if patterns is not None else get_resolver().url_patterns:
        route = prefix + str(pattern.pattern)
        if route.startswith(SKIPPED_PREFIXES):
            continue
        if isinstance(pattern, URLResolver):
            yield from concrete_paths(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern):
            if "format" in route:
                continue  # variantes ".json" do router do DRF, mesma view
            # O router do DRF escreve as rotas como regex: "^aplicadores/(?P<pk>[^/.]+)/$".
            path = route.replace("(?P<pk>[^/.]+)", "1").replace("^", "").replace("$", "")
            for converter, value in (("<int:pk>", "1"), ("<str:kind>", "unit")):
                path = path.replace(converter, value)
            yield pattern.name, "/" + path


class LoginRequiredTests(TestCase):
    def test_the_walk_found_the_routes(self):
        names = {name for name, _ in concrete_paths()}
        self.assertTrue({"dashboard", "entry_list", "summary", "upload", "settings", "list"} <= names)

    def test_every_route_rejects_an_anonymous_visitor(self):
        for name, path in concrete_paths():
            if name in PUBLIC:
                continue
            with self.subTest(path=path):
                response = self.client.get(path)
                if path.startswith("/api/"):
                    self.assertEqual(response.status_code, 403)
                else:
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response["Location"].startswith("/login/"), response["Location"])

    def test_login_page_is_public(self):
        self.assertEqual(self.client.get("/login/").status_code, 200)


class PostOnlyTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("admin", password="admin")
        self.client.force_login(user)

    def test_deletions_refuse_get(self):
        for path in POST_ONLY:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)
