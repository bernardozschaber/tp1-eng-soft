"""Service entries ("lançamentos") and the import batches that created them."""
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.applicators.models import Applicator
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.calculator import TaxRates, compute_breakdown
from apps.payroll.schedule import payment_date_for


class ImportBatch(models.Model):
    """One uploaded payment-list workbook, kept for traceability."""

    file_name = models.CharField("arquivo", max_length=255)
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self) -> str:
        return self.file_name


class ServiceRole(models.TextChoices):
    APPLICATOR = "APLICADOR", "Aplicador"
    ADVISOR = "ORIENTADOR", "Orientador"
    FLOATER = "VOLANTE", "Volante"


class Shift(models.TextChoices):
    MORNING = "MANHA", "Manhã"
    AFTERNOON = "TARDE", "Tarde"
    EVENING = "NOITE", "Noite"


MONEY = {"max_digits": 10, "decimal_places": 2}


class ServiceEntry(models.Model):
    """A single service rendered by an applicator on a given date."""

    applicator = models.ForeignKey(Applicator, on_delete=models.PROTECT, related_name="entries", verbose_name="aplicador")
    role = models.CharField("função", max_length=12, choices=ServiceRole.choices, default=ServiceRole.APPLICATOR)
    activity_date = models.DateField("data da atividade")
    event_name = models.CharField("prova/evento", max_length=150)
    segment = models.CharField("segmento", max_length=80, blank=True)
    shift = models.CharField("horário", max_length=6, choices=Shift.choices, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, verbose_name="setor solicitante")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="unidade")
    # Snapshot of unit.paying_company at save time so history survives catalog edits.
    paying_company = models.ForeignKey(PayingCompany, on_delete=models.PROTECT, verbose_name="empresa pagadora")
    payment_date = models.DateField("data de pagamento")

    net_amount = models.DecimalField("valor líquido", **MONEY)
    gross_amount = models.DecimalField("valor bruto (RPA)", **MONEY, editable=False)
    inss_amount = models.DecimalField("INSS", **MONEY, editable=False)
    iss_amount = models.DecimalField("ISS", **MONEY, editable=False)
    ir_amount = models.DecimalField("IR", **MONEY, editable=False, default=Decimal("0"))

    notes = models.CharField("observações", max_length=255, blank=True)
    import_batch = models.ForeignKey(ImportBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-activity_date", "applicator__full_name"]
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"

    def __str__(self) -> str:
        return f"{self.applicator} · {self.event_name} · {self.activity_date:%d/%m/%Y}"

    # -- derived values -------------------------------------------------

    @property
    def total_withheld(self) -> Decimal:
        return self.inss_amount + self.iss_amount + self.ir_amount

    @property
    def net_payable(self) -> Decimal:
        return self.gross_amount - self.total_withheld

    @property
    def is_consistent(self) -> bool:
        return abs(self.net_payable - self.net_amount) < Decimal("1")

    def apply_calculations(self) -> None:
        """Fills derived fields from net_amount, unit and activity_date."""
        tax = TaxSettings.current()
        rates = TaxRates.from_percentages(tax.inss_rate, tax.iss_rate, tax.ir_rate)
        breakdown = compute_breakdown(self.net_amount, rates)
        self.gross_amount = breakdown.gross_amount
        self.inss_amount = breakdown.inss_amount
        self.iss_amount = breakdown.iss_amount
        self.ir_amount = breakdown.ir_amount
        self.paying_company = self.unit.paying_company
        if not self.payment_date:
            self.payment_date = payment_date_for(self.activity_date)

    def save(self, *args, **kwargs):
        self.apply_calculations()
        super().save(*args, **kwargs)
