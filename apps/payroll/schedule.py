"""
Payment calendar rule inherited from the spreadsheet:

  activity on day 1..15  -> paid on the 5th of the following month
  activity on day 16..31 -> paid on the 20th of the following month
"""
from datetime import date

FIRST_HALF_PAY_DAY = 5
SECOND_HALF_PAY_DAY = 20
MID_MONTH = 15


def next_month(reference: date) -> tuple[int, int]:
    if reference.month == 12:
        return reference.year + 1, 1
    return reference.year, reference.month + 1


def payment_date_for(activity_date: date) -> date:
    year, month = next_month(activity_date)
    pay_day = FIRST_HALF_PAY_DAY if activity_date.day <= MID_MONTH else SECOND_HALF_PAY_DAY
    return date(year, month, pay_day)


MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def previous_month(reference: date) -> tuple[int, int]:
    if reference.month == 1:
        return reference.year - 1, 12
    return reference.year, reference.month - 1


def fortnight_label(payment_date: date, with_year: bool = False) -> str:
    """
    Name of the fortnight a payment settles, as the legacy sheet titles it:
    a payment on the 5th closes the first half of the previous month, one on
    the 20th closes the second half. The year is only spelled out when the
    caller knows a report covers more than one.
    """
    ordinal = "1ª" if payment_date.day <= MID_MONTH else "2ª"
    year, month = previous_month(payment_date)
    suffix = f"/{year}" if with_year else ""
    return f"{ordinal} quinzena de {MONTH_NAMES[month - 1]}{suffix}"
