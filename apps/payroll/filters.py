"""Query-string filtering shared by the entry list, the summary and the export."""
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Q, QuerySet

from apps.payroll.models import ServiceEntry


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


@dataclass
class EntryFilters:
    """Filters parsed from request.GET; every field is optional."""

    query: str = ""
    unit_id: int | None = None
    company_id: int | None = None
    sector_id: int | None = None
    applicator_id: int | None = None
    payment_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    inconsistent_only: bool = False
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_request(cls, params) -> "EntryFilters":
        return cls(
            query=params.get("q", "").strip(),
            unit_id=_parse_int(params.get("unit")),
            company_id=_parse_int(params.get("company")),
            sector_id=_parse_int(params.get("sector")),
            applicator_id=_parse_int(params.get("applicator")),
            payment_date=_parse_date(params.get("payment_date")),
            date_from=_parse_date(params.get("from")),
            date_to=_parse_date(params.get("to")),
            inconsistent_only=params.get("inconsistent") == "1",
            raw={key: value for key, value in params.items() if value},
        )

    def apply(self, queryset: QuerySet[ServiceEntry] | None = None) -> QuerySet[ServiceEntry]:
        queryset = queryset if queryset is not None else ServiceEntry.objects.all()
        queryset = queryset.select_related("applicator", "unit", "sector", "paying_company")
        if self.query:
            queryset = queryset.filter(
                Q(applicator__full_name__icontains=self.query)
                | Q(event_name__icontains=self.query)
                | Q(unit__name__icontains=self.query)
                | Q(notes__icontains=self.query)
            )
        if self.unit_id:
            queryset = queryset.filter(unit_id=self.unit_id)
        if self.company_id:
            queryset = queryset.filter(paying_company_id=self.company_id)
        if self.sector_id:
            queryset = queryset.filter(sector_id=self.sector_id)
        if self.applicator_id:
            queryset = queryset.filter(applicator_id=self.applicator_id)
        if self.payment_date:
            queryset = queryset.filter(payment_date=self.payment_date)
        if self.date_from:
            queryset = queryset.filter(activity_date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(activity_date__lte=self.date_to)
        return queryset

    def querystring(self) -> str:
        from urllib.parse import urlencode

        return urlencode({key: value for key, value in self.raw.items() if key != "page"})
