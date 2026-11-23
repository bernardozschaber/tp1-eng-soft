"""Item 4 do roteiro de TESTES.md: as perguntas da prévia e a confirmação.

`merge_questions` e `creation_questions` decidem se duas grafias são uma
pessoa ou duas; errar paga em dobro por outro caminho. Os testes montam a
prévia direto no formato JSON que a sessão guarda, sem passar por planilha:
o parser tem os próprios testes em `test_parser.py`.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from apps.imports.services import (
    _amount_from,
    _follow_chains,
    _short_date,
)

DAY = "2026-09-15"


# --- funções puras -----------------------------------------------------------


class SmallHelpersTests(SimpleTestCase):
    def test_typed_amounts(self):
        self.assertEqual(_amount_from("85"), Decimal("85"))
        self.assertEqual(_amount_from("R$ 85,50"), Decimal("85.50"))
        self.assertEqual(_amount_from("1.234,5"), Decimal("1234.5"))
        self.assertEqual(_amount_from("", fallback=Decimal("7")), Decimal("7"))
        self.assertEqual(_amount_from("a combinar", fallback=Decimal("7")), Decimal("7"))

    def test_short_date(self):
        self.assertEqual(_short_date("2026-09-15"), "15/09/2026")
        self.assertEqual(_short_date(""), "sem data")
        self.assertEqual(_short_date("15 de setembro"), "15 de setembro")

    def test_chains_end_at_the_last_target(self):
        answers = {
            "FELIPE CARNEIRO": ("FELIPE CARDOSO", "name:Felipe Cardoso"),
            "FELIPE CARDOSO": ("FELIPE CARDOSO OLIVEIRA", "applicator:7"),
        }

        self.assertEqual(
            _follow_chains(answers),
            {"FELIPE CARNEIRO": "applicator:7", "FELIPE CARDOSO": "applicator:7"},
        )

    def test_a_cycle_does_not_loop_forever(self):
        answers = {"ANA A": ("ANA B", "name:Ana B"), "ANA B": ("ANA A", "name:Ana A")}

        self.assertEqual(set(_follow_chains(answers)), {"ANA A", "ANA B"})