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

from apps.applicators.models import Applicator, RegistrationStatus
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