"""
RPA (Recibo de Pagamento Autônomo) arithmetic.

The applicator is promised a NET amount. The RPA is issued on the GROSS
amount, from which INSS, ISS and IR are withheld, so:

    gross = net / (1 - inss - iss - ir)
    net_payable = gross - inss_amount - iss_amount - ir_amount  (== net)

The legacy spreadsheet added a ±R$0.01 "rounding adjustment"; by decision of
the finance team this system does NOT apply it.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
ONE_HUNDRED = Decimal("100")


@dataclass(frozen=True)
class TaxRates:
    """Withholding rates as fractions (0.11 == 11%)."""

    inss: Decimal
    iss: Decimal
    ir: Decimal = Decimal("0")

    @classmethod
    def from_percentages(cls, inss: Decimal, iss: Decimal, ir: Decimal = Decimal("0")) -> "TaxRates":
        return cls(inss=Decimal(inss) / ONE_HUNDRED, iss=Decimal(iss) / ONE_HUNDRED, ir=Decimal(ir) / ONE_HUNDRED)

    @property
    def total(self) -> Decimal:
        return self.inss + self.iss + self.ir

    @property
    def net_factor(self) -> Decimal:
        """Share of the gross that reaches the applicator (0.84 for 11% + 5%)."""
        return Decimal("1") - self.total


@dataclass(frozen=True)
class PayrollBreakdown:
    """Money amounts for a single service, all rounded to cents."""

    net_amount: Decimal
    gross_amount: Decimal
    inss_amount: Decimal
    iss_amount: Decimal
    ir_amount: Decimal

    @property
    def total_withheld(self) -> Decimal:
        return self.inss_amount + self.iss_amount + self.ir_amount

    @property
    def net_payable(self) -> Decimal:
        """What is actually paid: gross minus withholdings."""
        return self.gross_amount - self.total_withheld

    @property
    def difference(self) -> Decimal:
        """Gap between the promised net and the recomputed net (rounding noise)."""
        return self.net_payable - self.net_amount

    @property
    def is_consistent(self) -> bool:
        """Mirrors the spreadsheet check: |gross - taxes - net| must be below R$1."""
        return abs(self.difference) < Decimal("1")


def round_cents(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def compute_breakdown(net_amount: Decimal, rates: TaxRates) -> PayrollBreakdown:
    """Grosses up a net amount and splits the withholdings."""
    net_amount = Decimal(net_amount)
    if rates.net_factor <= 0:
        raise ValueError("Tax rates must sum to less than 100%.")
    gross = round_cents(net_amount / rates.net_factor)
    return PayrollBreakdown(
        net_amount=round_cents(net_amount),
        gross_amount=gross,
        inss_amount=round_cents(gross * rates.inss),
        iss_amount=round_cents(gross * rates.iss),
        ir_amount=round_cents(gross * rates.ir),
    )
