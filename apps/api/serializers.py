"""DRF serializers exposing the domain to the JSON API."""
from rest_framework import serializers

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.models import ServiceEntry


class PayingCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = PayingCompany
        fields = ["id", "name"]


class UnitSerializer(serializers.ModelSerializer):
    paying_company_name = serializers.CharField(source="paying_company.name", read_only=True)

    class Meta:
        model = Unit
        fields = ["id", "name", "paying_company", "paying_company_name", "is_default"]


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "name", "is_default"]


class TaxSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxSettings
        fields = ["inss_rate", "iss_rate", "ir_rate", "updated_at"]


class ApplicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Applicator
        fields = [
            "id", "full_name", "cpf", "email", "phone", "course", "institution",
            "bank_name", "bank_branch", "bank_account", "pix_key", "notes", "registration_status", "is_active",
        ]


class ServiceEntrySerializer(serializers.ModelSerializer):
    applicator_name = serializers.CharField(source="applicator.full_name", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    paying_company_name = serializers.CharField(source="paying_company.name", read_only=True)
    net_payable = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_consistent = serializers.BooleanField(read_only=True)
    # Optional on input: computed from activity_date when omitted.
    payment_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = ServiceEntry
        fields = [
            "id", "applicator", "applicator_name", "role", "activity_date", "event_name", "segment", "shift",
            "sector", "unit", "unit_name", "paying_company", "paying_company_name", "payment_date",
            "net_amount", "gross_amount", "inss_amount", "iss_amount", "ir_amount", "net_payable", "is_consistent",
            "notes", "import_batch", "created_at",
        ]
        read_only_fields = ["paying_company", "gross_amount", "inss_amount", "iss_amount", "ir_amount", "import_batch", "created_at"]

    def validate_net_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("O valor líquido deve ser maior que zero.")
        return value
