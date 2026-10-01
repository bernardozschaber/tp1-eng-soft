"""Applicator: the freelance exam proctor who receives RPA payments."""
from django.db import models

from apps.applicators.names import normalize_name
from apps.applicators.phones import display_phone, whatsapp_number


class RegistrationStatus(models.TextChoices):
    """Situação do cadastro, do jeito que o financeiro lê na lista.

    Só há dois estados porque só há duas perguntas na prática: esta pessoa já
    recebeu antes (cadastro conferido, pagamento recorrente) ou é a primeira
    vez que ela aparece numa lista (cadastro criado pela importação, ainda sem
    histórico). Quem confirma a criação na pré-visualização define o segundo.
    """

    ACTIVE = "ativo", "cadastro ativo: pagamento recorrente"
    NEW = "novo", "cadastro novo: primeiro pagamento"


class Applicator(models.Model):
    full_name = models.CharField("nome completo", max_length=150)
    # Upper-case, accent-free version of full_name used to match spreadsheet rows.
    normalized_name = models.CharField(max_length=150, unique=True, editable=False, db_index=True)
    cpf = models.CharField("CPF", max_length=14, blank=True)
    email = models.EmailField("e-mail", blank=True)
    phone = models.CharField("WhatsApp", max_length=20, blank=True)
    identity_document = models.CharField("identidade", max_length=30, blank=True)
    birth_date = models.DateField("data de nascimento", null=True, blank=True)
    gender = models.CharField("sexo", max_length=20, blank=True)
    neighborhood = models.CharField("bairro", max_length=80, blank=True)
    # "VSE" na planilha de agendamento: marca quem atende a unidade Vale do Sereno.
    vse = models.BooleanField("VSE", default=False)
    course = models.CharField("curso", max_length=100, blank=True)
    course_period = models.CharField("período", max_length=20, blank=True)
    institution = models.CharField("instituição", max_length=120, blank=True)
    bank_name = models.CharField("banco", max_length=80, blank=True)
    bank_branch = models.CharField("agência", max_length=20, blank=True)
    bank_account = models.CharField("conta", max_length=30, blank=True)
    account_type = models.CharField("tipo de conta", max_length=30, blank=True)
    pix_type = models.CharField("tipo de chave PIX", max_length=30, blank=True)
    pix_key = models.CharField("chave PIX", max_length=120, blank=True)
    pis_nit = models.CharField("PIS/NIT", max_length=30, blank=True)
    referral = models.CharField("indicação", max_length=120, blank=True)
    photo = models.CharField(
        "foto 3x4",
        max_length=120,
        blank=True,
        help_text='Caminho em static/, ex.: "img/aplicadores/fulano.jpeg".',
    )
    notes = models.TextField("observações", blank=True)
    # Todo cadastro nasce novo: só um pagamento gerado o torna recorrente.
    registration_status = models.CharField(
        "situação", max_length=10, choices=RegistrationStatus.choices, default=RegistrationStatus.NEW
    )
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "aplicador"
        verbose_name_plural = "aplicadores"

    def __str__(self) -> str:
        return self.full_name

    @property
    def is_new_registration(self) -> bool:
        return self.registration_status == RegistrationStatus.NEW

    @property
    def whatsapp_url(self) -> str:
        """Link direto para a conversa; vazio quando só há telefone fixo."""
        number = whatsapp_number(self.phone)
        return f"https://wa.me/{number}" if number else ""

    @property
    def whatsapp_display(self) -> str:
        return display_phone(self.phone)

    RECURRING_PAYMENTS = 2

    def promote_if_recurring(self) -> bool:
        """Deixa de ser "primeiro pagamento" quando aparece num segundo pagamento.

        A pessoa atravessa inteiro o primeiro fechamento com a etiqueta de
        estreante — é nele que alguém confere documento, banco e PIX pela
        primeira vez. Some quando ela entra numa segunda data de pagamento, que
        é o que "recorrente" quer dizer. Só sobe: um lançamento corrigido
        depois não devolve ninguém para a fila de estreantes.
        """
        if self.registration_status != RegistrationStatus.NEW:
            return False
        if self.entries.values("payment_date").distinct().count() < self.RECURRING_PAYMENTS:
            return False
        self.registration_status = RegistrationStatus.ACTIVE
        self.save(update_fields=["registration_status", "updated_at"])
        return True

    @property
    def bank_details(self) -> str:
        """"3824 / 01090861-6" — agência e conta como a planilha as escreve."""
        return " / ".join(part for part in (self.bank_branch, self.bank_account) if part)

    @property
    def initials(self) -> str:
        words = self.full_name.split()
        if not words:
            return "?"
        return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.full_name)
        super().save(*args, **kwargs)

    @classmethod
    def find_by_name(cls, raw_name: str) -> "Applicator | None":
        return cls.objects.filter(normalized_name=normalize_name(raw_name)).first()

    @classmethod
    def find_by_cpf(cls, cpf: str) -> "Applicator | None":
        """Casa pelo CPF, que é identidade de verdade — nome não é.

        Aceita o valor gravado com ou sem pontuação; CPF incompleto não casa
        com ninguém (devolveria o primeiro parecido, que é pior que nada).
        """
        digits = "".join(char for char in (cpf or "") if char.isdigit())
        if len(digits) != 11:
            return None
        formatted = f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return cls.objects.filter(cpf__in=[formatted, digits]).first()
