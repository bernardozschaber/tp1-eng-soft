"""Aggregations that feed the home dashboard."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum

from apps.applicators.models import RegistrationStatus
from apps.payroll.models import ServiceEntry

# The dashboard reasons in payment cycles ("quinzenas"), not in calendar days:
# every activity is paid on the 5th or the 20th, so a month is two payments.
PERIOD_OPTIONS = [
    ("PGTO", "Último pagamento", 1),
    ("MES", "Último mês", 2),
    ("3M", "Últimos 3 meses", 6),
    ("6M", "Últimos 6 meses", 12),
    ("1A", "Último ano", 24),
]
DEFAULT_PERIOD_KEY = "MES"


@dataclass(frozen=True)
class DashboardPeriod:
    key: str
    label: str
    cycles: int

    @classmethod
    def from_key(cls, key: str | None) -> "DashboardPeriod":
        wanted = key or DEFAULT_PERIOD_KEY
        for option_key, label, cycles in PERIOD_OPTIONS:
            if option_key == wanted:
                return cls(option_key, label, cycles)
        return cls.from_key(DEFAULT_PERIOD_KEY)

    @classmethod
    def options(cls) -> list[tuple[str, str]]:
        return [(key, label) for key, label, _ in PERIOD_OPTIONS]


def payment_cycles() -> list[date]:
    """Every payment date on record, most recent first."""
    return list(ServiceEntry.objects.order_by("-payment_date").values_list("payment_date", flat=True).distinct())


def _entries_for(payment_dates: list[date]):
    if not payment_dates:
        return ServiceEntry.objects.none()
    return ServiceEntry.objects.filter(payment_date__in=payment_dates)


def _sum(queryset, field: str) -> Decimal:
    return queryset.aggregate(total=Sum(field))["total"] or Decimal("0")


def cumulative_series(queryset) -> list[dict]:
    """Running total of net amounts per activity day, for the line chart."""
    rows = queryset.values("activity_date").annotate(total=Sum("net_amount")).order_by("activity_date")
    running = Decimal("0")
    series = []
    for row in rows:
        running += row["total"]
        series.append({"date": row["activity_date"].isoformat(), "value": float(running)})
    return series


def unit_weights(queryset) -> list[dict]:
    """Share of the net total per unit, in descending order."""
    grand_total = _sum(queryset, "net_amount")
    rows = (
        queryset.values("unit_id", "unit__name", "paying_company__name")
        .annotate(total=Sum("net_amount"), count=Count("id"))
        .order_by("-total")
    )
    weights = []
    for index, row in enumerate(rows):
        share = (row["total"] / grand_total * 100) if grand_total else Decimal("0")
        weights.append(
            {
                "id": row["unit_id"],
                "name": row["unit__name"],
                "company": row["paying_company__name"],
                "total": row["total"],
                "count": row["count"],
                "weight": share,
                "color_index": index % 8 + 1,
            }
        )
    return weights


def build_dashboard(period: DashboardPeriod) -> dict:
    cycles = payment_cycles()
    current_dates = cycles[: period.cycles]
    previous_dates = cycles[period.cycles : period.cycles * 2]
    current = _entries_for(current_dates)
    previous = _entries_for(previous_dates)
    current_net = _sum(current, "net_amount")
    previous_net = _sum(previous, "net_amount")
    change = current_net - previous_net
    change_percent = (change / previous_net * 100) if previous_net else None
    return {
        "period": period,
        "payment_dates": sorted(current_dates),
        "net_total": current_net,
        "gross_total": _sum(current, "gross_amount"),
        "withheld_total": _sum(current, "inss_amount") + _sum(current, "iss_amount") + _sum(current, "ir_amount"),
        "entry_count": current.count(),
        "applicator_count": current.values("applicator").distinct().count(),
        "change": change,
        "change_percent": change_percent,
        "series": cumulative_series(current),
        "unit_weights": unit_weights(current),
        "review_count": current.filter(applicator__registration_status=RegistrationStatus.NEW).values("applicator").distinct().count(),
    }
