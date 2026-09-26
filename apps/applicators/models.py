"""Applicator: the freelance exam proctor who receives RPA payments."""
from django.db import models

from apps.applicators.names import normalize_name


class Applicator(models.Model):
    full_name = models.CharField("nome completo", max_length=150)
    # Upper-case, accent-free version of full_name used to match spreadsheet rows.
    normalized_name = models.CharField(max_length=150, unique=True, editable=False, db_index=True)
    cpf = models.CharField("CPF", max_length=14, blank=True)
    email = models.EmailField("e-mail", blank=True)
    phone = models.CharField("telefone", max_length=20, blank=True)
    course = models.CharField("curso", max_length=100, blank=True)
    institution = models.CharField("instituição", max_length=120, blank=True)
    bank_name = models.CharField("banco", max_length=80, blank=True)
    bank_branch = models.CharField("agência", max_length=10, blank=True)
    bank_account = models.CharField("conta", max_length=20, blank=True)
    pix_key = models.CharField("chave PIX", max_length=120, blank=True)
    notes = models.TextField("observações", blank=True)
    # True when the record was auto-created by an import and still needs HR review.
    needs_review = models.BooleanField("cadastro incompleto", default=False)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "aplicador"
        verbose_name_plural = "aplicadores"

    def __str__(self) -> str:
        return self.full_name

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_name(self.full_name)
        super().save(*args, **kwargs)

    @classmethod
    def find_by_name(cls, raw_name: str) -> "Applicator | None":
        return cls.objects.filter(normalized_name=normalize_name(raw_name)).first()
