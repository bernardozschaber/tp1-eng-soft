"""Casamento de nomes: acento, maiúscula e as grafias que a planilha repete."""
from django.test import TestCase

from apps.applicators.names import (
    is_same_person,
    looks_like_same_person,
    name_tokens,
    normalize_name,
    strip_accents,
)


class NormalizeNameTests(TestCase):
    """`normalize_name` é a chave que decide se duas linhas são a mesma pessoa."""

    def test_strips_accents(self):
        self.assertEqual(strip_accents("Gusmão"), "Gusmao")

    def test_accent_variants_collapse_to_the_same_key(self):
        # O bug real: duas grafias do mesmo nome viravam dois cadastros.
        self.assertEqual(
            normalize_name("Gislaine Sousa Gusmão"),
            normalize_name("GISLAINE SOUSA GUSMAO"),
        )

    def test_collapses_repeated_whitespace(self):
        self.assertEqual(normalize_name("Ana   Luisa  de Souza"), "ANA LUISA DE SOUZA")

    def test_drops_parenthesised_suffix(self):
        self.assertEqual(normalize_name("Maria Silva (C.E. ONLINE)"), "MARIA SILVA")

    def test_name_tokens_splits_the_normalized_form(self):
        self.assertEqual(name_tokens("Ana de Souza"), ["ANA", "DE", "SOUZA"])


class SamePersonHeuristicsTests(TestCase):
    """`is_same_person` decide para casar planilhas; `looks_like_same_person` só pergunta."""

    def test_short_name_fits_inside_the_full_name(self):
        self.assertTrue(is_same_person("Isadora Godinho", "Isadora Godinho Andrade"))

    def test_tolerates_one_letter_typo(self):
        self.assertTrue(is_same_person("Larissa Linfgren", "Larissa Lindgren"))

    def test_does_not_match_a_different_middle_name(self):
        self.assertFalse(is_same_person("Ana Laura Deus Lopes", "Ana Rita Fagundes Amaral Lopes"))

    def test_looks_like_same_person_is_looser_than_is_same_person(self):
        # Mesmo primeiro e último nome, sobrenome do meio bem diferente: a
        # pergunta é levantada, mas a decisão automática não é tomada.
        self.assertTrue(looks_like_same_person("Felipe Cardoso Oliveira", "Felipe Carneiro Oliveira"))
        self.assertFalse(is_same_person("Felipe Cardoso Oliveira", "Felipe Carneiro Oliveira"))

    def test_single_word_names_never_match(self):
        self.assertFalse(looks_like_same_person("Ana", "Ana Luisa Souza"))
