"""
Reference data ("Cadastros" in the legacy spreadsheet): paying companies,
school units, requesting sectors and the tax rates used by the RPA calculator.
"""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class PayingCompany(models.Model):
    """Legal entity that issues the RPA payment (e.g. "RRPM Matriz")."""

    name = models.CharField("empresa pagadora", max_length=80, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "empresa pagadora"
        verbose_name_plural = "empresas pagadoras"

    def __str__(self) -> str:
        return self.name


class Unit(models.Model):
    """School unit where the activity happened. Each unit maps to one paying company."""

    name = models.CharField("unidade", max_length=80, unique=True)
    paying_company = models.ForeignKey(
        PayingCompany, on_delete=models.PROTECT, related_name="units", verbose_name="empresa pagadora"
    )
    is_default = models.BooleanField("padrão na importação", default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "unidade"
        verbose_name_plural = "unidades"

    def __str__(self) -> str:
        return self.name

    @property
    def short_name(self) -> str:
        """Código curto da unidade: LOURDES, CJ, GO, VSE.

        Sai da empresa pagadora ("RRPM CJ" -> "CJ"), que é onde a operação já
        abrevia as unidades. "Matriz" não nomeia unidade nenhuma, então a
        matriz aparece pelo próprio nome.
        """
        company = self.paying_company.name if self.paying_company_id else ""
        code = company.split()[-1].upper() if company else ""
        if not code or code == "MATRIZ":
            return self.name.upper()
        return code


class Sector(models.Model):
    """Department that requested the service (e.g. "APL. DE PROVAS", "ADM")."""

    name = models.CharField("setor solicitante", max_length=80, unique=True)
    is_default = models.BooleanField("padrão na importação", default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "setor solicitante"
        verbose_name_plural = "setores solicitantes"

    def __str__(self) -> str:
        return self.name


PERCENT_VALIDATORS = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]


class TaxSettings(models.Model):
    """
    Singleton holding the withholding rates applied on the RPA gross amount.
    Rates are stored as percentages (11.00 means 11%).
    """

    inss_rate = models.DecimalField("INSS (%)", max_digits=5, decimal_places=2, default=Decimal("11.00"), validators=PERCENT_VALIDATORS)
    iss_rate = models.DecimalField("ISS (%)", max_digits=5, decimal_places=2, default=Decimal("5.00"), validators=PERCENT_VALIDATORS)
    ir_rate = models.DecimalField("IR (%)", max_digits=5, decimal_places=2, default=Decimal("0.00"), validators=PERCENT_VALIDATORS)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "alíquotas"
        verbose_name_plural = "alíquotas"

    def __str__(self) -> str:
        return f"INSS {self.inss_rate}% · ISS {self.iss_rate}% · IR {self.ir_rate}%"

    @classmethod
    def current(cls) -> "TaxSettings":
        """Returns the single settings row, creating it with defaults on first use."""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce the singleton
        super().save(*args, **kwargs)
