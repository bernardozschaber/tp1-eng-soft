"""Defeitos que não pertencem a um app, e sim ao projeto inteiro."""
import re
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from apps.core.access import FULL_ACCESS_GROUP, allowed_sections, section_for_view

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
# O tokenizer do Django casa {# … #} sem DOTALL, então um comentário que
# atravessa a quebra de linha não é reconhecido como comentário.
TEMPLATE_COMMENT = re.compile(r"\{#.*?#\}", re.S)


class TemplateCommentTests(TestCase):
    """`{# … #}` só comenta uma linha.

    Escrito em duas, o Django não o reconhece e imprime o texto na página: já
    aconteceu na coluna de turno da lista de lançamentos e no card de nomes
    parecidos da importação, onde a nota de implementação apareceu para o
    operador no meio da pergunta que ele precisava responder. Nota de código
    longa vai em `{% comment %}`.

    O teste varre os templates em vez de cobrir uma tela, porque o erro é fácil
    de repetir em qualquer arquivo e invisível em revisão de diff.
    """

    def test_no_template_comment_spans_lines(self):
        offenders = []
        for template in sorted(TEMPLATES_DIR.rglob("*.html")):
            source = template.read_text(encoding="utf-8")
            for match in TEMPLATE_COMMENT.finditer(source):
                if "\n" in match.group(0):
                    line = source[: match.start()].count("\n") + 1
                    offenders.append(f"{template.relative_to(TEMPLATES_DIR.parent)}:{line}")
        self.assertEqual(
            offenders, [],
            "comentário {# … #} em mais de uma linha vaza para a página; "
            f"use {{% comment %}}: {', '.join(offenders)}",
        )


class SectionForViewTests(TestCase):
    """A chave de seção que o menu e o middleware compartilham."""

    def test_payroll_summary_is_its_own_section(self):
        self.assertEqual(section_for_view("payroll", "payroll:summary"), "summary")

    def test_payroll_entries_are_not_summary(self):
        self.assertEqual(section_for_view("payroll", "payroll:entry_list"), "payroll")

    def test_catalog_maps_to_settings(self):
        self.assertEqual(section_for_view("catalog", "catalog:settings"), "settings")

    def test_dashboard_has_no_section(self):
        self.assertEqual(section_for_view("", "dashboard"), "")


class AllowedSectionsTests(TestCase):
    """Grupo de acesso total vê tudo; os demais, só a própria seção."""

    def setUp(self):
        User = get_user_model()
        self.full_access_user = User.objects.create_user("jessica.moreira")
        self.full_access_user.groups.add(Group.objects.create(name=FULL_ACCESS_GROUP))
        self.restricted_user = User.objects.create_user("fernanda.rezende")
        self.restricted_user.groups.add(Group.objects.create(name="Gestor financeiro"))
        self.no_group_user = User.objects.create_user("sem.grupo")

    def test_full_access_group_sees_every_section(self):
        self.assertEqual(allowed_sections(self.full_access_user), {"applicators", "imports", "payroll", "summary", "settings"})

    def test_superuser_sees_every_section_without_a_group(self):
        superuser = get_user_model().objects.create_superuser("admin", password="admin")
        self.assertEqual(allowed_sections(superuser), {"applicators", "imports", "payroll", "summary", "settings"})

    def test_gestor_financeiro_sees_only_its_own_sections(self):
        self.assertEqual(allowed_sections(self.restricted_user), {"payroll", "summary", "settings"})

    def test_user_with_no_group_sees_nothing(self):
        self.assertEqual(allowed_sections(self.no_group_user), set())


class SectionAccessMiddlewareTests(TestCase):
    """De ponta a ponta: o middleware barra a URL, não só esconde o menu."""

    def setUp(self):
        User = get_user_model()
        self.rh_user = User.objects.create_user("felipe.oliveira", password="5424")
        self.rh_user.groups.add(Group.objects.create(name="Usuário do RH"))
        self.finance_user = User.objects.create_user("fernanda.rezende", password="1387")
        self.finance_user.groups.add(Group.objects.create(name="Gestor financeiro"))

    def test_user_outside_the_section_is_redirected_to_dashboard(self):
        self.client.login(username="felipe.oliveira", password="5424")
        response = self.client.get("/configuracoes/", follow=True)
        self.assertRedirects(response, "/")

    def test_user_inside_the_section_is_not_redirected(self):
        self.client.login(username="fernanda.rezende", password="1387")
        response = self.client.get("/configuracoes/")
        self.assertEqual(response.status_code, 200)


class SeedTeamRenameTests(TestCase):
    """Quem mudou de usuário (fernanda -> fernanda.rezende) é renomeado, não duplicado."""

    def test_rerunning_seed_team_renames_the_old_username_keeping_the_pk(self):
        old_user = get_user_model().objects.create_user("fernanda")
        old_pk = old_user.pk

        call_command("seed_team", stdout=StringIO())

        self.assertFalse(get_user_model().objects.filter(username="fernanda").exists())
        renamed = get_user_model().objects.get(username="fernanda.rezende")
        self.assertEqual(renamed.pk, old_pk)
        self.assertEqual(renamed.profile.role, "Gestor financeiro")
        self.assertIn("Gestor financeiro", renamed.groups.values_list("name", flat=True))

    def test_rerunning_seed_team_does_not_duplicate_an_already_renamed_user(self):
        call_command("seed_team", stdout=StringIO())
        call_command("seed_team", stdout=StringIO())

        self.assertEqual(get_user_model().objects.filter(username="fernanda.rezende").count(), 1)
