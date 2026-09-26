"""Brazilian currency / date formatting filters."""
from decimal import Decimal

from django import template

register = template.Library()


def format_brl(value, symbol: bool = True) -> str:
    """Decimal('1234.5') -> 'R$1.234,50' (or '1.234,50' without symbol)."""
    if value is None or value == "":
        return "—"
    amount = Decimal(value).quantize(Decimal("0.01"))
    negative = amount < 0
    integer_part, _, fraction = f"{abs(amount):.2f}".partition(".")
    groups = []
    while integer_part:
        groups.insert(0, integer_part[-3:])
        integer_part = integer_part[:-3]
    text = ".".join(groups) + "," + fraction
    prefix = "-" if negative else ""
    return f"{prefix}R${text}" if symbol else f"{prefix}{text}"


@register.filter
def brl(value):
    return format_brl(value)


@register.filter
def brl_plain(value):
    return format_brl(value, symbol=False)


@register.filter
def percent(value):
    if value is None:
        return "—"
    return f"{Decimal(value).normalize():f}".replace(".", ",") + "%"


@register.filter
def initials(name: str) -> str:
    words = [word for word in (name or "").split() if word]
    if not words:
        return "?"
    return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()
