"""
Popula o banco com uma operação fictícia, para quem abre o sistema pela
primeira vez encontrar as telas cheias e poder explorá-las.

    python manage.py seed_demo            # cria; recusa se já houver dados
    python manage.py seed_demo --reset    # apaga os cadastros antes

Os dados são inventados — nome e CPF não pertencem a ninguém. O sorteio é
determinístico (`random.Random(SEED)`), então duas máquinas que rodam o comando
veem exatamente os mesmos cadastros, o que também serve para conferir a demo.

Não substitui `seed`: as unidades, os setores e as alíquotas continuam vindo de
lá, e este comando falha se elas não existirem.
"""
import random
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.applicators.models import Applicator
from apps.catalog.models import Sector, Unit

SEED = 20260930

FIRST_NAMES = [
    "Ana Luiza", "Bruno", "Camila", "Daniel", "Eduarda", "Felipe", "Gabriela",
    "Henrique", "Isabela", "João Pedro", "Karina", "Leonardo", "Mariana",
    "Nathalia", "Otávio", "Paula", "Rafael", "Sofia", "Thiago", "Vitória",
    "Arthur", "Beatriz", "Caio", "Débora", "Emanuel", "Fernanda", "Gustavo",
    "Helena", "Igor", "Juliana", "Larissa", "Matheus",
]
LAST_NAMES = [
    "Almeida", "Barbosa", "Carvalho", "Dias", "Esteves", "Ferreira", "Gomes",
    "Horta", "Innocenti", "Junqueira", "Lacerda", "Machado", "Nogueira",
    "Oliveira", "Prado", "Queiroz", "Rezende", "Siqueira", "Teixeira", "Vasconcelos",
]


def cpf_check_digits(base: str) -> str:
    """Os dois dígitos verificadores de um CPF, para os números da demo serem válidos."""
    digits = [int(char) for char in base]
    for length in (9, 10):
        total = sum(digit * (length + 1 - index) for index, digit in enumerate(digits[:length]))
        remainder = total * 10 % 11
        digits.append(0 if remainder == 10 else remainder)
    return f"{digits[9]}{digits[10]}"


def format_cpf(base: str) -> str:
    full = base + cpf_check_digits(base)
    return f"{full[:3]}.{full[3:6]}.{full[6:9]}-{full[9:]}"


class Command(BaseCommand):
    help = "Popula o banco com aplicadores e lançamentos fictícios, para explorar o sistema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="apaga os cadastros atuais antes de criar os novos"
        )
        parser.add_argument(
            "--applicators", type=int, default=32, help="quantos aplicadores criar (padrão: 32)"
        )

    def handle(self, *args, **options):
        if not Unit.objects.exists() or not Sector.objects.exists():
            raise CommandError("Rode `python manage.py seed` antes: faltam unidades ou setores.")

        if options["reset"]:
            deleted, _ = Applicator.objects.all().delete()
            self.stdout.write(f"{deleted} cadastros antigos apagados.")
        elif Applicator.objects.exists():
            raise CommandError("Já há aplicadores no banco. Use --reset para substituí-los.")

        rng = random.Random(SEED)
        with transaction.atomic():
            applicators = self.create_applicators(rng, options["applicators"])

        self.stdout.write(self.style.SUCCESS(f"{len(applicators)} aplicadores criados."))

    def create_applicators(self, rng: random.Random, wanted: int) -> list[Applicator]:
        """Cria os cadastros, cada um com nome, CPF, contato e nascimento."""
        names: list[str] = []
        while len(names) < wanted:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in names:
                names.append(name)

        applicators = []
        for name in sorted(names):
            first_name = name.split()[0].lower().replace(" ", "")
            applicator = Applicator(
                full_name=name,
                cpf=format_cpf(f"{rng.randrange(100_000_000, 999_999_999):09d}"),
                email=f"{first_name}.{name.split()[-1].lower()}@email.com",
                phone=f"31 9{rng.randrange(1000, 9999)}-{rng.randrange(1000, 9999)}",
                identity_document=f"MG-{rng.randrange(10, 99)}.{rng.randrange(100, 999)}.{rng.randrange(100, 999)}",
                birth_date=date(rng.randrange(1996, 2006), rng.randrange(1, 13), rng.randrange(1, 29)),
                gender=rng.choice(["Feminino", "Masculino"]),
            )
            applicator.save()
            applicators.append(applicator)
        return applicators
