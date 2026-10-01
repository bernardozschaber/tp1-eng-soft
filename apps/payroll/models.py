"""Service entries ("lançamentos") and the import batches that created them."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.applicators.models import Applicator
from apps.applicators.names import strip_accents
from apps.catalog.models import PayingCompany, Sector, TaxSettings, Unit
from apps.payroll.calculator import TaxRates, compute_breakdown
from apps.payroll.schedule import payment_date_for


def event_key(event_name: str) -> str:
    """Chave de comparação do evento: maiúsculas, sem acento, espaço simples.

    Existe porque a mesma atividade chega escrita de formas que só diferem no
    enfeite — "Oficina de Redação", "OFICINA DE REDACAO", um espaço a mais no
    fim — e duas grafias do mesmo evento não podem valer como dois serviços.
    """
    return " ".join(strip_accents(event_name or "").upper().split())


class DuplicateServiceEntry(ValidationError):
    """Alguém tentou lançar um serviço que já está lançado.

    É `ValidationError` para que formulário e admin a mostrem como erro de
    campo em vez de página de erro, e é uma classe própria para que quem grava
    em lote — a importação — possa distinguir "esta linha já existe" de
    qualquer outro problema de validação e seguir para a próxima.
    """


class ImportBatch(models.Model):
    """One uploaded payment-list workbook, kept for traceability."""

    file_name = models.CharField("arquivo", max_length=255)
    # A planilha como ela chegou. Guardada para a pré-visualização poder mostrar
    # o documento de origem, e não só o que o parser entendeu dele.
    source_file = models.FileField("planilha original", upload_to="imports/%Y/%m/", blank=True)
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
    activity_date = models.DateField("data da atividade", db_index=True)
    event_name = models.CharField("prova/evento", max_length=150)
    # Versão canônica de event_name, usada só pela restrição de unicidade.
    event_key = models.CharField(max_length=150, editable=False, default="")
    segment = models.CharField("segmento", max_length=80, blank=True)
    shift = models.CharField("horário", max_length=6, choices=Shift.choices, blank=True)
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, verbose_name="setor solicitante")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="unidade")
    # Snapshot of unit.paying_company at save time so history survives catalog edits.
    paying_company = models.ForeignKey(PayingCompany, on_delete=models.PROTECT, verbose_name="empresa pagadora")
    payment_date = models.DateField("data de pagamento", db_index=True)

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
        indexes = [
            # The summary and the export group by (payment_date, applicator) and
            # read in that order; a composite index serves both the grouping and
            # the ordering without a sort step.
            models.Index(fields=["payment_date", "applicator"], name="entry_paydate_applicator"),
        ]
        constraints = [
            # Uma pessoa não presta o mesmo serviço duas vezes: um turno de um
            # dia é um turno só. Quando a mesma atividade chega em duas listas
            # — e chega, porque a operação copia a planilha da semana anterior
            # e esquece de trocar a data de alguma aba — o segundo lançamento
            # não é um serviço a mais, é o mesmo serviço contado de novo, e ele
            # inflaria o pagamento da pessoa. A regra fica no banco porque é
            # onde nenhuma tela, importação ou script passa por cima dela.
            models.UniqueConstraint(
                fields=["applicator", "activity_date", "event_key", "shift", "role", "unit"],
                name="entry_one_service_per_shift",
            ),
        ]

    # Os campos que dizem "é o mesmo serviço", na ordem da restrição.
    IDENTITY_FIELDS = ("applicator", "activity_date", "event_key", "shift", "role", "unit")

    def __str__(self) -> str:
        return f"{self.applicator} · {self.event_name} · {self.activity_date:%d/%m/%Y}"

    @classmethod
    def find_duplicate(cls, *, applicator, activity_date, event_name, shift, role, unit, exclude_pk=None):
        """O lançamento que já registra este mesmo serviço, se houver.

        A importação e o formulário perguntam antes de gravar para poderem
        explicar o que aconteceu; a restrição do banco é a garantia, não o
        aviso. `exclude_pk` deixa uma edição salvar sobre si mesma.
        """
        queryset = cls.objects.filter(
            applicator=applicator,
            activity_date=activity_date,
            event_key=event_key(event_name),
            shift=shift or "",
            role=role,
            unit=unit,
        )
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.first()

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
        self.event_name = (self.event_name or "").strip()
        self.event_key = event_key(self.event_name)
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

    def check_not_duplicate(self) -> None:
        """Recusa a gravação se este serviço já estiver lançado.

        A restrição do banco sozinha bastaria para impedir a duplicata, mas ela
        avisa tarde e mal: estoura um `IntegrityError` com o nome das colunas, e
        dentro de uma transação — a da importação, por exemplo — já deixou a
        transação inutilizável, derrubando junto o que foi gravado antes. A
        checagem aqui acontece antes do INSERT, então nada se perde e quem
        chamou recebe uma frase que explica o que houve.
        """
        existing = self.find_duplicate(
            applicator=self.applicator, activity_date=self.activity_date,
            event_name=self.event_name, shift=self.shift, role=self.role,
            unit=self.unit, exclude_pk=self.pk,
        )
        if existing is None:
            return
        raise DuplicateServiceEntry(
            f"{self.applicator} já tem um lançamento de \u201c{existing.event_name}\u201d em "
            f"{existing.activity_date:%d/%m/%Y}, no turno da {existing.get_shift_display() or 'sem turno'}, "
            f"como {existing.get_role_display().lower()} na unidade {existing.unit.name} "
            f"(lançamento #{existing.pk}). O mesmo serviço não pode ser lançado duas vezes — "
            f"edite o lançamento que já existe."
        )

    def save(self, *args, **kwargs):
        self.apply_calculations()
        is_new_entry = self._state.adding
        self.check_not_duplicate()
        super().save(*args, **kwargs)
        # Um lançamento novo pode ser o segundo pagamento da pessoa — o que
        # tira dela a etiqueta de estreante.
        if is_new_entry:
            self.applicator.promote_if_recurring()
