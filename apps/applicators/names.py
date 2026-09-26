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
