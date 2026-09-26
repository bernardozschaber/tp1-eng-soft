"""REST API (session-authenticated). Browsable at /api/."""
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from apps.api.serializers import (
    ApplicatorSerializer, PayingCompanySerializer, SectorSerializer, ServiceEntrySerializer,
    TaxSettingsSerializer, UnitSerializer,
)
from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.filters import EntryFilters
from apps.payroll.summary import build_summary, grand_totals


class ApplicatorViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicatorSerializer
    queryset = Applicator.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        return queryset.filter(full_name__icontains=query) if query else queryset


class ServiceEntryViewSet(viewsets.ModelViewSet):
    """Supports the same query-string filters as the web listing (unit, company, payment_date, from, to, q)."""

    serializer_class = ServiceEntrySerializer
    queryset = ServiceEntrySerializer.Meta.model.objects.all()

    def get_queryset(self):
        return EntryFilters.from_request(self.request.query_params).apply()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Payment summary grouped by payment date > applicator > company."""
        groups = build_summary(self.get_queryset())
        payload = [
            {
                "payment_date": group.payment_date,
                "rows": [
                    {
                        "applicator_id": row.applicator_id, "applicator": row.applicator_name, "company": row.company_name,
                        "gross": row.gross, "inss": row.inss, "iss": row.iss, "ir": row.ir,
                        "net_payable": row.net_payable, "entries": row.entry_count, "consistent": row.is_consistent,
                    }
                    for row in group.rows
                ],
                "totals": {"gross": group.gross_total, "withheld": group.total("withheld"), "net_payable": group.net_payable_total},
            }
            for group in groups
        ]
        return Response({"groups": payload, "totals": grand_totals(groups)})


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UnitSerializer
    queryset = Unit.objects.select_related("paying_company")


class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SectorSerializer
    queryset = Sector.objects.all()


class PayingCompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayingCompanySerializer
    queryset = PayingCompany.objects.all()


@api_view(["GET"])
def tax_settings(request):
    return Response(TaxSettingsSerializer(TaxSettings.current()).data)
