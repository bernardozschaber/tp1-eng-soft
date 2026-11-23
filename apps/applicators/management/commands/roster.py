"""Carrega a lista conferida de aplicadores — a fonte da verdade dos nomes.

Quem entra por aqui fica como "cadastro ativo: pagamento recorrente". O que
chegar depois por importação e não casar com essa lista vira pergunta na
pré-visualização, e só vira cadastro ("cadastro novo: primeiro pagamento")
quando alguém confirma.

    # das planilhas do setor: quem já recebeu, com a ficha de quem tem ficha
    manage.py roster --payments "...RPAS....xlsm" --profiles "...Agendamento....xlsm" --replace

    # de uma lista simples, um nome por linha
    manage.py roster nomes.txt
    cat nomes.txt | manage.py roster -
"""
import sys

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.applicators.models import Applicator, RegistrationStatus
from apps.applicators.names import normalize_name, to_display_name
from apps.applicators.spreadsheets import match_profiles, read_payment_names, read_profiles
from apps.payroll.models import ServiceEntry


class Command(BaseCommand):
    help = "Carrega a lista conferida de aplicadores (planilhas do setor ou arquivo de nomes)."

    def add_arguments(self, parser):
        parser.add_argument("source", nargs="?", help='arquivo com um nome por linha, ou "-" para a entrada padrão')
        parser.add_argument("--payments", help='planilha de controle de RPAs (aba "RESUMO DE PGTO POR APLICADOR")')
        parser.add_argument("--profiles", help='planilha de agendamento (aba "Aplicadores"), que completa as fichas')
        parser.add_argument(
            "--replace", action="store_true",
            help="apaga os cadastros atuais antes de carregar (recusa se houver lançamentos ligados a eles)",
        )

    def handle(self, *args, **options):
        if bool(options["source"]) == bool(options["payments"]):
            raise CommandError("Informe um arquivo de nomes OU --payments (não os dois).")
        if options["profiles"] and not options["payments"]:
            raise CommandError("--profiles só faz sentido junto com --payments.")

        names = (
            read_payment_names(options["payments"]) if options["payments"] else self._read_names(options["source"])
        )
        if not names:
            raise CommandError("Nenhum nome na entrada.")
        profiles = read_profiles(options["profiles"]) if options["profiles"] else []
        matched, ambiguous = match_profiles(names, profiles) if profiles else ({}, {})

        with transaction.atomic():
            if options["replace"]:
                self._purge()
            created, updated, merged, enriched = self._load(names, matched)

        self.stdout.write(self.style.SUCCESS(f"{created} cadastro(s) criado(s), {updated} atualizado(s)."))
        if profiles:
            self.stdout.write(f"{enriched} cadastro(s) com ficha completa, de {len(profiles)} ficha(s) lidas.")
            self.stdout.write(f"{len(names) - enriched - merged} nome(s) sem ficha correspondente.")
        if merged:
            self.stdout.write(f"{merged} grafia(s) juntada(s) a um cadastro que a ficha identificou como a mesma pessoa.")
        for key, candidates in ambiguous.items():
            self.stdout.write(self.style.WARNING(
                f"Ambíguo, ficha não aplicada: {key} casa com {', '.join(profile.name for profile in candidates)}."
            ))

    # --- carga -------------------------------------------------------------

    def _load(self, names: list[str], matched: dict) -> tuple[int, int, int, int]:
        """Um cadastro por pessoa: a ficha é que diz quando duas grafias são uma só."""
        created = updated = merged = enriched = 0
        # Duas grafias que casam com a mesma ficha ("Isadora Godinho" e
        # "Isadora Godinho Andrade") são a mesma pessoa, e a ficha manda no nome.
        seen_profiles: dict[str, Applicator] = {}
        for name in names:
            key = normalize_name(name)
            profile = matched.get(key)
            if profile and profile.normalized in seen_profiles:
                merged += 1
                continue
            display = to_display_name(profile.name if profile else name)
            applicator, was_created = Applicator.objects.get_or_create(
                normalized_name=normalize_name(display),
                defaults={"full_name": display, "registration_status": RegistrationStatus.ACTIVE},
            )
            if was_created:
                created += 1
            else:
                applicator.full_name = display
                applicator.registration_status = RegistrationStatus.ACTIVE
                updated += 1
            if profile:
                for attribute, value in profile.fields.items():
                    setattr(applicator, attribute, value)
                enriched += 1
                seen_profiles[profile.normalized] = applicator
            applicator.save()
        return created, updated, merged, enriched

    # --- entrada de texto --------------------------------------------------

    def _read_names(self, source: str) -> list[str]:
        handle = sys.stdin if source == "-" else open(source, encoding="utf-8")
        try:
            lines = handle.read().splitlines()
        finally:
            if handle is not sys.stdin:
                handle.close()
        names, seen = [], set()
        for line in lines:
            name = " ".join(line.strip().split())
            if not name or name.startswith("#"):
                continue
            key = normalize_name(name)
            if key in seen:
                continue
            seen.add(key)
            names.append(name)
        return names

    def _purge(self) -> None:
        blocked = ServiceEntry.objects.count()
        if blocked:
            raise CommandError(
                f"Há {blocked} lançamento(s) ligados aos cadastros atuais. "
                "Apague as importações em /importar antes de substituir a lista."
            )
        deleted, _ = Applicator.objects.all().delete()
        self.stdout.write(f"{deleted} cadastro(s) antigo(s) removido(s).")
