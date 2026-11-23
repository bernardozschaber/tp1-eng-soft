"""Quem está por trás de cada login: foto, cargo e contato."""
from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Dados de apresentação de um usuário do sistema.

    A foto é guardada como caminho dentro de ``static/`` (e não como
    ``ImageField``) porque o time entrega os retratos junto com o código: não há
    upload, nem servidor de mídia, nem dependência de Pillow.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="usuário",
    )
    role = models.CharField("cargo", max_length=120, blank=True)
    unit = models.ForeignKey(
        "catalog.Unit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profiles",
        verbose_name="unidade",
    )
    email = models.EmailField("e-mail", blank=True)
    phone = models.CharField("telefone", max_length=32, blank=True)
    photo = models.CharField(
        "foto",
        max_length=120,
        blank=True,
        help_text='Caminho em static/, ex.: "img/avatars/jessica.jpeg".',
    )

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        return self.user.get_full_name() or self.user.username

    @property
    def contact_email(self) -> str:
        return self.email or self.user.email

    @property
    def meta_line(self) -> str:
        """"Cargo · Unidade" para o rodapé da navegação; cai para o que houver.

        O código da unidade some quando o cargo já o cita por extenso (ex.:
        "Aplicação de Provas (VSE)") — repeti-lo só ocuparia espaço à toa numa
        linha que já é curta para caber sem reticências.
        """
        unit_code = self.unit.short_name if self.unit_id else ""
        if unit_code and unit_code.upper() in self.role.upper():
            unit_code = ""
        parts = [part for part in (self.role, unit_code) if part]
        return " · ".join(parts)
