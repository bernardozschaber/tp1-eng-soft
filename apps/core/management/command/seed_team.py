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