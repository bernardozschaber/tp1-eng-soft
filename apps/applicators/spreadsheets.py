"""Lê as duas planilhas do setor que formam o cadastro de aplicadores.

São duas fontes com papéis diferentes:

* a planilha de controle de RPAs, aba "RESUMO DE PGTO POR APLICADOR", diz
  **quem já recebeu** — é ela que define quem entra no cadastro;
* a planilha de agendamento, aba "Aplicadores", diz **o que se sabe** sobre
  cada pessoa (documentos, banco, curso) — é a ficha que preenche o perfil.

A segunda não cria ninguém: só completa quem a primeira já trouxe.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from apps.applicators.names import is_same_person, normalize_name

PAYMENTS_SHEET = "RESUMO DE PGTO POR APLICADOR"
PAYMENTS_NAME_COLUMN = "APLICADOR"
PROFILES_SHEET = "Aplicadores"
# Os cabeçalhos da ficha, como estão escritos na linha 2 da aba "Aplicadores".
PROFILE_COLUMNS = {
    "nome": "Nome",
    "phone": "Telefone",
    "cpf": "CPF",
    "identity_document": "Identidade",
    "birth_date": "Data Nascimento",
    "gender": "Sexo",
    "neighborhood": "Bairro",
    "vse": "VSE",
    "email": "E-mail",
    "course": "Curso",
    "course_period": "Período",
    "institution": "Instituição",
    "bank_details": "Dados bancários",
    "bank_name": "Banco:",
    "account_type": "Tipo de conta",
    "pix_type": "Tipo PIX",
    "pix_key": "PIX",
    "pis_nit": "PIS / NIT",
    "referral": "Indicação",
}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split())


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(_text(value), pattern).date()
        except ValueError:
            continue
    return None


def read_payment_names(path: str | Path) -> list[str]:
    """Nomes da coluna APLICADOR, na ordem em que aparecem, sem repetir.

    A aba repete o bloco de cabeçalho a cada quinzena, então a leitura é por
    conteúdo da coluna, não por posição: cabeçalho e linha de total saem fora.
    """
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[PAYMENTS_SHEET]
        column = None
        names, seen = [], set()
        for row in worksheet.iter_rows(values_only=True):
            cells = [_text(value) for value in row]
            if PAYMENTS_NAME_COLUMN in [cell.upper() for cell in cells]:
                column = [cell.upper() for cell in cells].index(PAYMENTS_NAME_COLUMN)
                continue
            if column is None or column >= len(cells):
                continue
            name = cells[column]
            if not name or name.upper() in {PAYMENTS_NAME_COLUMN, "TOTAL"}:
                continue
            key = normalize_name(name)
            if not key or key in seen:
                continue
            seen.add(key)
            names.append(name)
        if column is None:
            raise ValueError(f'A aba "{PAYMENTS_SHEET}" não tem a coluna "{PAYMENTS_NAME_COLUMN}".')
        return names
    finally:
        workbook.close()


@dataclass
class Profile:
    """Uma linha da ficha de agendamento, já nos nomes de campo do modelo."""

    name: str
    fields: dict = field(default_factory=dict)

    @property
    def normalized(self) -> str:
        return normalize_name(self.name)


def _split_bank_details(value: str) -> tuple[str, str]:
    """"3824 / 01090861-6" -> ("3824", "01090861-6")."""
    branch, separator, account = value.partition("/")
    if not separator:
        return "", value.strip()
    return branch.strip(), account.strip()


def read_profiles(path: str | Path) -> list[Profile]:
    """Fichas da aba "Aplicadores", uma por pessoa, prontas para virar campos."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[PROFILES_SHEET]
        rows = list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    header_index, header = None, []
    for index, row in enumerate(rows):
        cells = [_text(value) for value in row]
        if PROFILE_COLUMNS["nome"] in cells and PROFILE_COLUMNS["cpf"] in cells:
            header_index, header = index, cells
            break
    if header_index is None:
        raise ValueError(f'A aba "{PROFILES_SHEET}" não tem a linha de cabeçalho esperada.')
    position = {key: header.index(label) for key, label in PROFILE_COLUMNS.items() if label in header}
    missing = sorted(set(PROFILE_COLUMNS) - set(position))
    if missing:
        raise ValueError(f'Colunas ausentes na aba "{PROFILES_SHEET}": {", ".join(missing)}.')

    profiles = []
    for row in rows[header_index + 1 :]:
        cells = [_text(value) for value in row]
        name = cells[position["nome"]] if position["nome"] < len(cells) else ""
        if not name:
            continue
        values = {key: (cells[index] if index < len(cells) else "") for key, index in position.items()}
        branch, account = _split_bank_details(values["bank_details"])
        raw_birth = row[position["birth_date"]] if position["birth_date"] < len(row) else None
        profiles.append(Profile(name=name, fields={
            "phone": values["phone"],
            "cpf": values["cpf"],
            "identity_document": values["identity_document"],
            "birth_date": _as_date(raw_birth),
            "gender": values["gender"],
            "neighborhood": values["neighborhood"],
            # A coluna é um "X" quando a pessoa atende o Vale do Sereno.
            "vse": values["vse"].strip().upper().startswith("X"),
            "email": values["email"],
            "course": values["course"],
            "course_period": values["course_period"],
            "institution": values["institution"],
            "bank_branch": branch,
            "bank_account": account,
            "bank_name": values["bank_name"],
            "account_type": values["account_type"],
            "pix_type": values["pix_type"],
            "pix_key": values["pix_key"],
            "pis_nit": values["pis_nit"],
            "referral": values["referral"],
        }))
    return profiles


def match_profiles(names: list[str], profiles: list[Profile]) -> tuple[dict[str, Profile], dict[str, list[Profile]]]:
    """Casa cada nome de pagamento com no máximo uma ficha.

    Devolve (casados, ambíguos). Nome que combina com duas fichas não é casado
    com nenhuma: entra no relatório para alguém olhar, porque escolher a
    primeira seria escrever o CPF de uma pessoa no cadastro de outra.
    """
    by_normalized = {profile.normalized: profile for profile in profiles}
    matched: dict[str, Profile] = {}
    ambiguous: dict[str, list[Profile]] = {}
    for name in names:
        key = normalize_name(name)
        exact = by_normalized.get(key)
        if exact:
            matched[key] = exact
            continue
        candidates = [profile for profile in profiles if is_same_person(key, profile.normalized)]
        if len(candidates) == 1:
            matched[key] = candidates[0]
        elif candidates:
            ambiguous[key] = candidates
    return matched, ambiguous
