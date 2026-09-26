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
