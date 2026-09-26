"""
"Resumo de pagamento por aplicador": groups entries by payment date,
applicator and paying company, exactly like the legacy RESUMO sheet.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.payroll.models import ServiceEntry

ZERO = Decimal("0")


@dataclass
class SummaryRow:
    payment_date: date
    applicator_id: int
    applicator_name: str
    company_name: str
    needs_review: bool
    gross: Decimal = ZERO
    inss: Decimal = ZERO
    iss: Decimal = ZERO
    ir: Decimal = ZERO
    net: Decimal = ZERO
    entry_count: int = 0
    events: list[str] = field(default_factory=list)

    @property
    def withheld(self) -> Decimal:
        return self.inss + self.iss + self.ir

    @property
    def net_payable(self) -> Decimal:
        return self.gross - self.withheld

    @property
    def is_consistent(self) -> bool:
        return abs(self.net_payable - self.net) < Decimal("1")

    def add(self, entry: ServiceEntry) -> None:
        self.gross += entry.gross_amount
        self.inss += entry.inss_amount
        self.iss += entry.iss_amount
        self.ir += entry.ir_amount
        self.net += entry.net_amount
        self.entry_count += 1
        if entry.event_name not in self.events:
            self.events.append(entry.event_name)


@dataclass
class SummaryGroup:
    """All rows that share one payment date (one block in the spreadsheet)."""

    payment_date: date
    rows: list[SummaryRow]

    def total(self, attribute: str) -> Decimal:
        return sum((getattr(row, attribute) for row in self.rows), ZERO)

    # Template-friendly totals (Django templates cannot call methods with arguments).
    @property
    def gross_total(self) -> Decimal:
        return self.total("gross")

    @property
    def inss_total(self) -> Decimal:
        return self.total("inss")

    @property
    def iss_total(self) -> Decimal:
        return self.total("iss")

    @property
    def ir_total(self) -> Decimal:
        return self.total("ir")

    @property
    def net_payable_total(self) -> Decimal:
        return self.total("net_payable")

    @property
    def entry_total(self) -> int:
        return sum(row.entry_count for row in self.rows)


def build_summary(queryset) -> list[SummaryGroup]:
    rows: dict[tuple, SummaryRow] = {}
    for entry in queryset.order_by("payment_date", "applicator__full_name"):
        key = (entry.payment_date, entry.applicator_id, entry.paying_company_id)
        if key not in rows:
            rows[key] = SummaryRow(
                payment_date=entry.payment_date,
                applicator_id=entry.applicator_id,
                applicator_name=entry.applicator.full_name,
                company_name=entry.paying_company.name,
                needs_review=entry.applicator.needs_review,
            )
        rows[key].add(entry)

    groups: dict[date, list[SummaryRow]] = {}
    for row in rows.values():
        groups.setdefault(row.payment_date, []).append(row)
    return [SummaryGroup(payment_date=day, rows=group_rows) for day, group_rows in sorted(groups.items())]


def grand_totals(groups: list[SummaryGroup]) -> dict[str, Decimal | int]:
    return {
        "gross": sum((group.total("gross") for group in groups), ZERO),
        "withheld": sum((group.total("withheld") for group in groups), ZERO),
        "net": sum((group.total("net") for group in groups), ZERO),
        "applicators": len({row.applicator_id for group in groups for row in group.rows}),
        "entries": sum(row.entry_count for group in groups for row in group.rows),
    }
