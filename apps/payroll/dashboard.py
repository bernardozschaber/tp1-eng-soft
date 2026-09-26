"""Aggregations that feed the home dashboard."""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum

from apps.payroll.models import ServiceEntry

PERIOD_OPTIONS = [
    ("30D", "Últimos 30 dias", 30),
    ("90D", "Últimos 90 dias", 90),
    ("180D", "Últimos 6 meses", 180),
    ("1Y", "Último ano", 365),
    ("ALL", "Tudo", None),
]


@dataclass(frozen=True)
class DashboardPeriod:
    key: str
    label: str
    days: int | None

    @classmethod
    def from_key(cls, key: str | None) -> "DashboardPeriod":
        for option_key, label, days in PERIOD_OPTIONS:
            if option_key == (key or "30D"):
                return cls(option_key, label, days)
        return cls(*PERIOD_OPTIONS[0])

    @classmethod
    def options(cls) -> list[tuple[str, str]]:
        return [(key, label) for key, label, _ in PERIOD_OPTIONS]

    @property
    def start(self) -> date | None:
        return None if self.days is None else date.today() - timedelta(days=self.days)

    @property
    def previous_start(self) -> date | None:
        return None if self.days is None else self.start - timedelta(days=self.days)


def _entries_between(start: date | None, end: date | None):
    queryset = ServiceEntry.objects.all()
    if start:
        queryset = queryset.filter(activity_date__gte=start)
    if end:
        queryset = queryset.filter(activity_date__lt=end)
    return queryset


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
    rows = queryset.values("unit__name").annotate(total=Sum("net_amount"), count=Count("id")).order_by("-total")
    weights = []
    for index, row in enumerate(rows):
        share = (row["total"] / grand_total * 100) if grand_total else Decimal("0")
        weights.append({"name": row["unit__name"], "total": row["total"], "count": row["count"], "weight": share, "color_index": index % 8 + 1})
    return weights


def build_dashboard(period: DashboardPeriod) -> dict:
    current = _entries_between(period.start, None)
    previous = _entries_between(period.previous_start, period.start) if period.days else ServiceEntry.objects.none()
    current_net = _sum(current, "net_amount")
    previous_net = _sum(previous, "net_amount")
    change = current_net - previous_net
    change_percent = (change / previous_net * 100) if previous_net else None
    return {
        "period": period,
        "net_total": current_net,
        "gross_total": _sum(current, "gross_amount"),
        "withheld_total": _sum(current, "inss_amount") + _sum(current, "iss_amount") + _sum(current, "ir_amount"),
        "entry_count": current.count(),
        "applicator_count": current.values("applicator").distinct().count(),
        "change": change,
        "change_percent": change_percent,
        "series": cumulative_series(current),
        "unit_weights": unit_weights(current),
        "review_count": current.filter(applicator__needs_review=True).values("applicator").distinct().count(),
    }
