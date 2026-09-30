"""
Popula o banco com uma operação fictícia inteira, para quem abre o sistema pela
primeira vez encontrar as telas cheias e poder explorá-las.

    python manage.py seed_demo            # cria; recusa se já houver dados
    python manage.py seed_demo --reset    # apaga lançamentos e aplicadores antes

Os dados são inventados — nome, CPF, banco e PIX não pertencem a ninguém — mas
seguem a forma dos reais: seis meses de atividade, doze quinzenas fechadas, as
quatro unidades, vários setores solicitantes e as três funções. O sorteio é
determinístico (`random.Random(SEED)`), então duas máquinas que rodam o comando
veem exatamente os mesmos números, o que também serve para conferir a demo.

Não substitui `seed`: as unidades, os setores e as alíquotas continuam vindo de
lá, e este comando falha se elas não existirem.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.applicators.models import Applicator
from apps.catalog.models import Sector, Unit
from apps.payroll.models import DuplicateServiceEntry, ImportBatch, ServiceEntry, ServiceRole, Shift

SEED = 20260930

# Seis meses de atividade dão doze quinzenas: o suficiente para o Resumo ter
# histórico e para os filtros de período do painel mudarem de resposta.
MONTHS_OF_HISTORY = 6

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
COURSES = [
    ("Medicina", "UFMG"), ("Direito", "PUC Minas"), ("Engenharia Civil", "CEFET-MG"),
    ("Letras", "UFMG"), ("Psicologia", "Newton Paiva"), ("Administração", "Ibmec"),
    ("Arquitetura", "UFMG"), ("Ciência da Computação", "PUC Minas"),
    ("Fisioterapia", "UFMG"), ("Publicidade", "UNA"),
]
NEIGHBORHOODS = [
    "Savassi", "Funcionários", "Santo Antônio", "Buritis", "Serra", "Cidade Nova",
    "Pampulha", "Gutierrez", "Sion", "Floresta", "Vila da Serra", "Castelo",
]
BANKS = ["Banco do Brasil", "Bradesco", "Caixa Econômica", "Itaú", "Nubank", "Santander"]
PERIODS = ["Manhã", "Noite", "Integral"]

# (nome do evento, setor solicitante, segmento) — o setor é o que pediu a
# atividade, e é por ele que o financeiro separa a conta no fechamento.
EVENTS = [
    ("Prova Regular", "APL. DE PROVAS", "Ensino Médio"),
    ("Simulado ENEM", "APL. DE PROVAS", "Pré-vestibular"),
    ("Prova Bimestral", "APL. DE PROVAS", "Ensino Fundamental II"),
    ("Avaliação Diagnóstica", "PEDAGÓGICO", "Ensino Médio"),
    ("Oficina de Redação", "PEDAGÓGICO", "Pré-vestibular"),
    ("Simulado Medicina", "APL. DE PROVAS", "Pré-vestibular"),
    ("Processo Seletivo Bolsas", "SECRETARIA - REGULATÓRIO", "Ensino Médio"),
    ("Feira de Profissões", "MKT", ""),
    ("Olimpíada de Matemática", "CDM", "Ensino Fundamental II"),
    ("Recuperação Semestral", "ADM", "Ensino Médio"),
]

# Peso de cada unidade no volume de trabalho: Lourdes é a matriz e concentra a
# maior parte das aplicações, como na operação real.
UNIT_WEIGHTS = [("Lourdes", 10), ("Cidade Jardim", 5), ("Santo Antônio", 3), ("Vale do Sereno", 2)]

# (função, peso no sorteio, valor líquido mínimo, máximo) — orientador ganha
# mais que aplicador, volante menos, e cada turno cai num valor "redondo".
ROLE_PROFILE = [
    (ServiceRole.APPLICATOR, 12, 120, 190),
    (ServiceRole.ADVISOR, 3, 200, 280),
    (ServiceRole.FLOATER, 2, 90, 130),
]

SHIFTS = [(Shift.MORNING, 5), (Shift.AFTERNOON, 4), (Shift.EVENING, 2)]

# Nome dos arquivos de onde os lançamentos "vieram", um por quinzena fechada:
# dá o que clicar na coluna de origem da lista de lançamentos.
BATCH_FILE_TEMPLATE = "Relatório de Atividade - {unit} - {label}.xlsx"


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


def fortnight_ranges(today: date, months: int) -> list[tuple[date, date, str]]:
    """As quinzenas fechadas dos últimos `months` meses, da mais antiga para a mais nova.

    Uma quinzena só entra quando terminou: a demo não inventa atividade em dia
    que ainda não aconteceu, para o "Último pagamento" do painel bater com o
    que a lista mostra.
    """
    ranges: list[tuple[date, date, str]] = []
    month_index = today.year * 12 + (today.month - 1)
    for offset in range(months, -1, -1):
        year, month = divmod(month_index - offset, 12)
        month += 1
        last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
        for start, end, half in ((1, 15, "1ª"), (16, last_day, "2ª")):
            first, final = date(year, month, start), date(year, month, end)
            if final < today:
                ranges.append((first, final, f"{half} quinzena {month:02d}-{year}"))
    return ranges


def weighted(rng: random.Random, options: list[tuple]) -> tuple:
    """Sorteia uma das opções `(valor, peso, ...)` respeitando os pesos."""
    return rng.choices(options, weights=[option[1] for option in options])[0]


class Command(BaseCommand):
    help = "Popula o banco com aplicadores e lançamentos fictícios, para explorar o sistema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="apaga lançamentos, lotes de importação e aplicadores antes de criar os novos",
        )
        parser.add_argument(
            "--applicators", type=int, default=32, help="quantos aplicadores criar (padrão: 32)"
        )

    def handle(self, *args, **options):
        units = {unit.name: unit for unit in Unit.objects.all()}
        sectors = {sector.name: sector for sector in Sector.objects.all()}
        if not units or not sectors:
            raise CommandError("Rode `python manage.py seed` antes: faltam unidades ou setores.")

        if options["reset"]:
            deleted, _ = ServiceEntry.objects.all().delete()
            ImportBatch.objects.all().delete()
            Applicator.objects.all().delete()
            self.stdout.write(f"{deleted} registros antigos apagados.")
        elif ServiceEntry.objects.exists() or Applicator.objects.exists():
            raise CommandError(
                "Já há aplicadores ou lançamentos no banco. Use --reset para substituí-los."
            )

        rng = random.Random(SEED)
        with transaction.atomic():
            applicators = self.create_applicators(rng, options["applicators"])
            entries = self.create_entries(rng, applicators, units, sectors)

        self.stdout.write(self.style.SUCCESS(
            f"{len(applicators)} aplicadores e {len(entries)} lançamentos criados."
        ))

    # -- cadastros ------------------------------------------------------

    def create_applicators(self, rng: random.Random, wanted: int) -> list[Applicator]:
        """Cria os cadastros com ficha completa, menos alguns deixados pela metade.

        Uns poucos ficam sem banco e sem PIX de propósito: é assim que a lista
        real chega ao financeiro, e é o que dá o que conferir na ficha.
        """
        names: list[str] = []
        while len(names) < wanted:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in names:
                names.append(name)

        applicators = []
        for index, name in enumerate(sorted(names)):
            course, institution = rng.choice(COURSES)
            incomplete = index % 9 == 0  # ~1 em 9 chega sem dados bancários
            first_name = name.split()[0].lower().replace(" ", "")
            applicator = Applicator(
                full_name=name,
                cpf=format_cpf(f"{rng.randrange(100_000_000, 999_999_999):09d}"),
                email=f"{first_name}.{name.split()[-1].lower()}@email.com",
                phone=f"31 9{rng.randrange(1000, 9999)}-{rng.randrange(1000, 9999)}",
                identity_document=f"MG-{rng.randrange(10, 99)}.{rng.randrange(100, 999)}.{rng.randrange(100, 999)}",
                birth_date=date(rng.randrange(1996, 2006), rng.randrange(1, 13), rng.randrange(1, 29)),
                gender=rng.choice(["Feminino", "Masculino"]),
                neighborhood=rng.choice(NEIGHBORHOODS),
                vse=rng.random() < 0.3,
                course=course,
                course_period=rng.choice(PERIODS),
                institution=institution,
                bank_name="" if incomplete else rng.choice(BANKS),
                bank_branch="" if incomplete else f"{rng.randrange(1000, 9999)}",
                bank_account="" if incomplete else f"{rng.randrange(10000, 99999)}-{rng.randrange(0, 9)}",
                account_type="" if incomplete else rng.choice(["Corrente", "Poupança"]),
                pix_type="" if incomplete else rng.choice(["CPF", "E-mail", "Celular"]),
                pix_key="" if incomplete else f"{first_name}.{name.split()[-1].lower()}@email.com",
                pis_nit="" if incomplete else f"{rng.randrange(100, 999)}.{rng.randrange(10000, 99999)}.{rng.randrange(10, 99)}-{rng.randrange(0, 9)}",
                referral=rng.choice(["", "", "Indicação de colega", "Site do colégio", "Instagram"]),
                notes="Cadastro incompleto: falta banco e PIX." if incomplete else "",
            )
            applicator.save()
            applicators.append(applicator)
        return applicators

    # -- lançamentos ----------------------------------------------------

    def create_entries(self, rng, applicators, units, sectors) -> list[ServiceEntry]:
        """Distribui as atividades pelas quinzenas fechadas dos últimos meses.

        A escala é a mesma de um fechamento de verdade: cada quinzena tem duas
        ou três atividades, cada atividade convoca uma parte da equipe, e uma
        pessoa pode pegar mais de um turno no mesmo dia. Quem entra por último
        só aparece na quinzena mais recente — e continua marcado como primeiro
        pagamento, que é o estado que o financeiro precisa ver na lista.
        """
        entries: list[ServiceEntry] = []
        periods = fortnight_ranges(date.today(), MONTHS_OF_HISTORY)
        # Os últimos cadastros da lista só entram nas quinzenas finais, para a
        # demo ter gente recorrente e gente estreando ao mesmo tempo.
        veterans = applicators[: len(applicators) - 6]
        for period_index, (first_day, last_day, label) in enumerate(periods):
            pool = veterans if period_index < len(periods) - 1 else applicators
            for _ in range(rng.randrange(2, 4)):
                unit = units[weighted(rng, UNIT_WEIGHTS)[0]]
                batch = ImportBatch.objects.create(
                    file_name=BATCH_FILE_TEMPLATE.format(unit=unit.short_name, label=label)
                )
                entries += self.create_activity(rng, pool, unit, sectors, first_day, last_day, batch)
        return entries

    def create_activity(self, rng, pool, unit, sectors, first_day, last_day, batch) -> list[ServiceEntry]:
        """Uma atividade: um evento, um dia, uma unidade e a equipe convocada."""
        event_name, sector_name, segment = rng.choice(EVENTS)
        sector = sectors.get(sector_name) or sectors["APL. DE PROVAS"]
        span = (last_day - first_day).days
        activity_date = first_day + timedelta(days=rng.randrange(span + 1))
        team = rng.sample(pool, k=min(len(pool), rng.randrange(6, 13)))

        created = []
        for applicator in team:
            role, _, low, high = weighted(rng, ROLE_PROFILE)
            shifts = [weighted(rng, SHIFTS)[0]]
            if rng.random() < 0.25:  # quem faz o dia inteiro pega dois turnos
                shifts.append(Shift.AFTERNOON if shifts[0] == Shift.MORNING else Shift.MORNING)
            for shift in shifts:
                entry = ServiceEntry(
                    applicator=applicator,
                    role=role,
                    activity_date=activity_date,
                    event_name=event_name,
                    segment=segment,
                    shift=shift,
                    sector=sector,
                    unit=unit,
                    net_amount=Decimal(rng.randrange(low, high + 1, 5)),
                    import_batch=batch,
                )
                try:
                    entry.save()
                except DuplicateServiceEntry:
                    continue  # o sorteio repetiu o mesmo turno; um turno é um só
                created.append(entry)
        return created
