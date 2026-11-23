"""Junta cadastros que são a mesma pessoa gravada duas vezes.

`Applicator.normalized_name` é única desde a criação da tabela e o `save()` a
recalcula sempre — então hoje, pela ORM, "Gislaine Sousa Gusmão" e "Gislaine
Sousa Gusmao" não conseguem virar dois cadastros. Mas linhas que entraram por
fora da ORM (restauração de backup, carga direta no banco) podem ter gravado
`normalized_name` sem passar por `normalize_name`, e aí a constraint nunca viu
os dois nomes como iguais. Este comando acha esses pares pelo nome recalculado
na hora, junta os lançamentos no cadastro mais usado e apaga o duplicado.

    manage.py dedupe_names          # só mostra o que juntaria
    manage.py dedupe_names --apply  # junta de verdade
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.applicators.models import Applicator, RegistrationStatus
from apps.applicators.names import normalize_name
from apps.payroll.models import ServiceEntry


class Command(BaseCommand):
    help = "Junta cadastros de aplicador que só diferem por acento/maiúscula no nome."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="grava a junção (sem isso, só mostra o que faria)")

    def handle(self, *args, **options):
        groups: dict[str, list[Applicator]] = defaultdict(list)
        for applicator in Applicator.objects.all():
            groups[normalize_name(applicator.full_name)].append(applicator)
        duplicates = {key: rows for key, rows in groups.items() if len(rows) > 1}

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("Nenhum nome duplicado encontrado."))
            return

        for key, rows in duplicates.items():
            survivor, losers = self._pick_survivor(rows)
            self.stdout.write(f"{key}: mantém #{survivor.pk} ({survivor.full_name}), "
                               f"junta {', '.join(f'#{row.pk}' for row in losers)}")
            if options["apply"]:
                with transaction.atomic():
                    self._merge(survivor, losers)

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Nada foi gravado; rode com --apply para juntar de verdade."))

    def _pick_survivor(self, rows: list[Applicator]) -> tuple[Applicator, list[Applicator]]:
        """O cadastro com mais lançamentos vence; empate resolve pelo mais antigo."""
        counts = {row.pk: row.entries.count() for row in rows}
        survivor = max(rows, key=lambda row: (counts[row.pk], -row.pk))
        return survivor, [row for row in rows if row.pk != survivor.pk]

    def _merge(self, survivor: Applicator, losers: list[Applicator]) -> None:
        for loser in losers:
            ServiceEntry.objects.filter(applicator=loser).update(applicator=survivor)
            if loser.registration_status == RegistrationStatus.ACTIVE:
                survivor.registration_status = RegistrationStatus.ACTIVE
            loser.delete()
        survivor.save()  # recalcula normalized_name, garantindo que fica correto
