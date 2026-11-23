from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(blank=True, max_length=120, verbose_name="cargo")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="e-mail")),
                ("phone", models.CharField(blank=True, max_length=32, verbose_name="telefone")),
                (
                    "photo",
                    models.CharField(
                        blank=True,
                        help_text='Caminho em static/, ex.: "img/avatars/jessica.jpeg".',
                        max_length=120,
                        verbose_name="foto",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuário",
                    ),
                ),
            ],
            options={"verbose_name": "perfil", "verbose_name_plural": "perfis"},
        ),
    ]
