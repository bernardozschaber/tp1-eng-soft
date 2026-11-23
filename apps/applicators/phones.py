"""Descobre, no telefone cadastrado, qual número serve para falar no WhatsApp.

A ficha do setor guarda o telefone como a pessoa escreveu na inscrição, e
muita gente escreveu dois: o fixo de casa e o celular ("3657-6258 / 31
99444-9630"). Só o celular tem WhatsApp, então é ele que vira o link.
"""
import re

# As fichas são de Belo Horizonte; um celular escrito sem DDD é daqui.
DEFAULT_AREA_CODE = "31"
COUNTRY_CODE = "55"
_SEPARATORS = re.compile(r"[/;,]|\se\s")


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _is_mobile(digits: str) -> bool:
    """Celular brasileiro: nove dígitos começando em 9, com ou sem o DDD na frente."""
    if len(digits) == 11:
        return digits[2] == "9"
    return len(digits) == 9 and digits[0] == "9"


def whatsapp_number(raw_phone: str) -> str:
    """Devolve o celular com DDI e DDD ("5531994449630"), ou "" se não houver.

    Fixo é descartado: mandar mensagem para ele não chega a lugar nenhum. Sem
    DDD, o número herda o DDD do outro telefone da mesma ficha — e, na falta
    dele, o da praça.
    """
    candidates = [_digits(part) for part in _SEPARATORS.split(raw_phone or "")]
    area_codes = [digits[:2] for digits in candidates if len(digits) in (10, 11)]
    for digits in candidates:
        if not _is_mobile(digits):
            continue
        if len(digits) == 9:
            digits = (area_codes[0] if area_codes else DEFAULT_AREA_CODE) + digits
        return COUNTRY_CODE + digits
    return ""


def display_phone(raw_phone: str) -> str:
    """O número que o link usa, escrito como se lê: "(31) 99444-9630"."""
    number = whatsapp_number(raw_phone)
    if not number:
        return ""
    area, first, last = number[2:4], number[4:-4], number[-4:]
    return f"({area}) {first}-{last}"
