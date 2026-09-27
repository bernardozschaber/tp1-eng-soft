"""Defeitos que não pertencem a um app, e sim ao projeto inteiro."""
import re
from pathlib import Path

from django.test import TestCase

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