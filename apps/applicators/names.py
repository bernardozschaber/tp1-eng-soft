"""Helpers to normalize applicator names coming from spreadsheets."""
import re
import unicodedata

# Trailing parenthesised qualifiers, e.g. "MARIA X (C.E. ONLINE)".
_SUFFIX_PATTERN = re.compile(r"\s*\(([^)]*)\)\s*$")
# Portuguese connectors that stay lower-case in display names.
_LOWERCASE_WORDS = {"de", "da", "do", "das", "dos", "e"}


def split_suffix(raw_name: str) -> tuple[str, str]:
    """Separates "NAME (QUALIFIER)" into ("NAME", "QUALIFIER")."""
    match = _SUFFIX_PATTERN.search(raw_name)
    if not match:
        return raw_name.strip(), ""
    return raw_name[: match.start()].strip(), match.group(1).strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_name(raw_name: str) -> str:
    """Canonical matching key: upper-case, no accents, single spaces, no suffix."""
    base, _ = split_suffix(raw_name)
    return " ".join(strip_accents(base).upper().split())


def name_tokens(raw_name: str) -> list[str]:
    """Palavras do nome na forma canônica, para comparar pedaço a pedaço."""
    return normalize_name(raw_name).split()


def looks_like_same_person(one: str, other: str) -> bool:
    """Diz se dois nomes *podem* ser a mesma pessoa — não que sejam.

    As listas escrevem a mesma pessoa de dois jeitos: "Larissa Maia" numa aba e
    "Larissa Salgado Maia" em outra. Dois casos cobrem o que aparece na prática:
    um nome é o começo do outro em palavras inteiras, ou os dois têm o mesmo
    primeiro e o mesmo último nome. Nomes de uma palavra só ficam de fora — com
    um "Ana" qualquer par pareceria plausível.

    A heurística é deliberadamente generosa e nunca decide sozinha: ela só
    levanta a pergunta que o operador responde na pré-visualização. "Felipe
    Cardoso Oliveira" e "Felipe Carneiro Oliveira" entram aqui, e a resposta
    certa pode muito bem ser "são duas pessoas".
    """
    first, second = name_tokens(one), name_tokens(other)
    if not first or not second or first == second:
        return False
    if len(first) < 2 or len(second) < 2:
        return False
    shorter, longer = (first, second) if len(first) <= len(second) else (second, first)
    if longer[: len(shorter)] == shorter:
        return True
    return shorter[0] == longer[0] and shorter[-1] == longer[-1]


def to_display_name(raw_name: str) -> str:
    """"ANA LUISA DE SOUZA" -> "Ana Luisa de Souza"."""
    base, _ = split_suffix(raw_name)
    words = base.split()
    result = []
    for index, word in enumerate(words):
        lowered = word.lower()
        if index > 0 and lowered in _LOWERCASE_WORDS:
            result.append(lowered)
        else:
            result.append(lowered.capitalize())
    return " ".join(result)


def _within_one_edit(one: str, other: str) -> bool:
    """Diz se duas palavras diferem por no máximo uma letra ("LINFGREN"/"LINDGREN")."""
    if abs(len(one) - len(other)) > 1:
        return False
    if one == other:
        return True
    shorter, longer = (one, other) if len(one) <= len(other) else (other, one)
    index = offset = 0
    edits = 0
    while index < len(shorter) and index + offset < len(longer):
        if shorter[index] == longer[index + offset]:
            index += 1
            continue
        edits += 1
        if edits > 1:
            return False
        if len(shorter) == len(longer):
            index += 1
        else:
            offset += 1
    return True


def _token_matches(one: str, other: str) -> bool:
    """Duas palavras do mesmo nome: iguais, inicial de uma abreviação, ou um erro de digitação."""
    if one == other:
        return True
    if len(one) <= 2 and other.startswith(one[0]):
        return True
    if len(other) <= 2 and one.startswith(other[0]):
        return True
    return len(one) >= 5 and len(other) >= 5 and _within_one_edit(one, other)


def is_same_person(one: str, other: str) -> bool:
    """Decide, e não só levanta a hipótese, se dois nomes são a mesma pessoa.

    Serve para casar a lista de pagamentos com a ficha de cadastro, onde não há
    CPF dos dois lados e ninguém vai conferir 250 pares à mão. É mais apertada
    que `looks_like_same_person`, que existe para *perguntar*: aqui o nome curto
    tem que caber inteiro no longo, palavra por palavra e na ordem, tolerando
    abreviação ("B. LUISA S. M. DE ASSIS") e uma letra trocada ("FEREIRA").
    Assim "Ana Laura Deus Lopes" não vira "Ana Rita Fagundes Amaral Lopes" só
    porque começam e terminam igual.
    """
    first, second = name_tokens(one), name_tokens(other)
    if not first or not second:
        return False
    shorter, longer = (first, second) if len(first) <= len(second) else (second, first)
    if len(shorter) < 2:
        return False
    # O nome curto é o começo do longo: "Isadora Godinho" / "Isadora Godinho Andrade".
    if longer[: len(shorter)] == shorter:
        return True
    if not _token_matches(first[0], second[0]) or not _token_matches(first[-1], second[-1]):
        return False
    position = 0
    for token in shorter:
        while position < len(longer) and not _token_matches(token, longer[position]):
            position += 1
        if position == len(longer):
            return False
        position += 1
    return True
