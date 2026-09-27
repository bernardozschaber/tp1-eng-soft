"""
Cria os logins da equipe de aplicação de provas, cada um com foto, cargo e
contato. A senha de cada pessoa é o PIN de quatro dígitos no fim do telefone;
o admin continua com a senha "admin". Pode rodar quantas vezes precisar.

    python manage.py seed_team
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.catalog.models import Unit
from apps.core.models import Profile

# (username, nome, sobrenome, e-mail, cargo, telefone, foto, nome da unidade)
# A senha sai dos quatro últimos dígitos do telefone — o PIN combinado com o time.
TEAM = [
    (
        "jessica.moreira",
        "Jessica",
        "Souza Moreira",
        "jessica.moreira@bernoulli.com.br",
        "♾️ Supervisor - Aplicação",
        "+55 31 8349-2433",
        "img/avatars/jessica.jpeg",
        "",
    ),
    (
        "fernanda",
        "Fernanda",
        "",
        "fernanda@bernoulli.com.br",
        "Aplicação de Provas (VSE)",
        "+55 31 9314-1387",
        "img/avatars/fernanda.jpeg",
        "Vale do Sereno",
    ),
    (
        "felipe",
        "Felipe",
        "",
        "felipe@bernoulli.com.br",
        "Aplicação de Provas (Lourdes)",
        "+55 31 8353-5424",
        "img/avatars/felipe.jpeg",
        "Lourdes",
    ),
    (
        "ana.julia",
        "Ana",
        "Júlia",
        "ana.julia@bernoulli.com.br",
        "Aplicação de Provas (CJ)",
        "+55 31 9350-0089",
        "img/avatars/ana-julia.jpeg",
        "Cidade Jardim",
    ),
    (
        "suzana.godoy",
        "Suzana",
        "Godoy",
        "suzana.godoy@bernoulli.com.br",
        "Coordenadora de Operações",
        "+55 31 9383-3608",
        "img/avatars/suzana.jpeg",
        "",
    ),
]

# O admin já existe (criado pelo `seed`); aqui ele só ganha rosto e cargo.
ADMIN_PROFILE = {
    "username": "admin",
    "first_name": "Bernardo",
    "last_name": "Zschaber",
    "email": "bernardo.zschaber@bernoulli.com.br",
    "role": "Administrador do sistema",
    "phone": "",
    "photo": "img/avatars/bernardo.jpeg",
}


def pin(phone: str) -> str:
    """Os quatro últimos dígitos do telefone, que é a senha da pessoa."""
    digits = [char for char in phone if char.isdigit()]
    return "".join(digits[-4:])


class Command(BaseCommand):
    help = "Cria os logins da equipe (senha = PIN do telefone) e o perfil do admin."

    def handle(self, *args, **options):
        User = get_user_model()

        for username, first_name, last_name, email, role, phone, photo, unit_name in TEAM:
            user, created = User.objects.get_or_create(username=username)
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.is_active = True
            user.set_password(pin(phone))
            user.save()
            unit = Unit.objects.filter(name=unit_name).first() if unit_name else None
            Profile.objects.update_or_create(
                user=user,
                defaults={"role": role, "email": email, "phone": phone, "photo": photo, "unit": unit},
            )
            verb = "criado" if created else "atualizado"
            self.stdout.write(f"{verb}: {username} (senha {pin(phone)}) — {role}")

        admin = User.objects.filter(username=ADMIN_PROFILE["username"]).first()
        if admin is None:
            self.stdout.write(self.style.WARNING("admin não encontrado; rode `python manage.py seed` antes."))
            return
        admin.first_name = ADMIN_PROFILE["first_name"]
        admin.last_name = ADMIN_PROFILE["last_name"]
        admin.email = ADMIN_PROFILE["email"]
        admin.save(update_fields=["first_name", "last_name", "email"])
        Profile.objects.update_or_create(
            user=admin,
            defaults={
                "role": ADMIN_PROFILE["role"],
                "email": ADMIN_PROFILE["email"],
                "phone": ADMIN_PROFILE["phone"],
                "photo": ADMIN_PROFILE["photo"],
            },
        )
        self.stdout.write(self.style.SUCCESS("Equipe pronta. Cada pessoa entra com o PIN do próprio telefone."))