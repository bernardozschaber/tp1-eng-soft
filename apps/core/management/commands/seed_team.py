"""
Cria os logins da equipe de aplicação de provas, cada um com foto, cargo e
contato. A senha de cada pessoa é o PIN de quatro dígitos no fim do telefone;
o admin continua com a senha "admin". Pode rodar quantas vezes precisar.

    python manage.py seed_team
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.catalog.models import Unit
from apps.core.access import FULL_ACCESS_GROUP, SECTION_GROUPS
from apps.core.models import Profile

# Usernames antigos que viraram outro: renomeia em vez de criar conta nova,
# para lançamentos e importações já gravados continuarem apontando pra pessoa certa.
RENAMED_USERNAMES = {
    "fernanda": "fernanda.rezende",
    "felipe": "felipe.oliveira",
}

# (username, nome, sobrenome, e-mail, cargo, telefone, foto, nome da unidade, grupo de acesso)
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
        FULL_ACCESS_GROUP,
    ),
    (
        "fernanda.rezende",
        "Fernanda",
        "Rezende",
        "fernanda.rezende@bernoulli.com.br",
        "Gestor financeiro",
        "+55 31 9314-1387",
        "img/avatars/fernanda.jpeg",
        "Vale do Sereno",
        SECTION_GROUPS["payroll"],
    ),
    (
        "felipe.oliveira",
        "Felipe",
        "Oliveira",
        "felipe.oliveira@bernoulli.com.br",
        "Usuário do RH",
        "+55 31 8353-5424",
        "img/avatars/felipe.jpeg",
        "Lourdes",
        SECTION_GROUPS["imports"],
    ),
    (
        "ana.julia",
        "Ana",
        "Júlia",
        "ana.julia@bernoulli.com.br",
        "Administrador financeiro",
        "+55 31 9350-0089",
        "img/avatars/ana-julia.jpeg",
        "Cidade Jardim",
        SECTION_GROUPS["applicators"],
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
        FULL_ACCESS_GROUP,
    ),
]

# O admin já existe (criado pelo `seed`); aqui ele só ganha rosto, cargo e acesso total.
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

        self._rename_existing(User)

        for username, first_name, last_name, email, role, phone, photo, unit_name, group_name in TEAM:
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
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.set([group])
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
        full_access, _ = Group.objects.get_or_create(name=FULL_ACCESS_GROUP)
        admin.groups.set([full_access])
        self.stdout.write(self.style.SUCCESS("Equipe pronta. Cada pessoa entra com o PIN do próprio telefone."))

    def _rename_existing(self, User) -> None:
        """Troca o username de quem mudou de função sem perder histórico (lançamentos, importações)."""
        for old, new in RENAMED_USERNAMES.items():
            if User.objects.filter(username=new).exists():
                continue
            user = User.objects.filter(username=old).first()
            if user is None:
                continue
            user.username = new
            user.save(update_fields=["username"])
            self.stdout.write(f"renomeado: {old} -> {new}")
