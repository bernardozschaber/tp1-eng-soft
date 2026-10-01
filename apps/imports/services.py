"""
Import workflow:

  1. `stage_uploads`    parse every uploaded workbook and keep a JSON-friendly
                        preview in the session (no database writes yet);
  2. `enrich_preview`   attach applicator matches, duplicate flags and the
                        computed gross amount so the preview page can show them;
  3. `merge_questions`  levanta os nomes parecidos entre si e com quem já está
                        cadastrado, para o operador confirmar um a um;
  4. `confirm_import`   read the (possibly edited) preview back from the POST
                        payload and persist entries, creating missing applicators.
"""
import hashlib
import uuid
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from apps.applicators.models import Applicator, RegistrationStatus
from apps.applicators.names import looks_like_same_person, name_tokens, normalize_name, split_suffix, to_display_name
from apps.catalog.models import Sector, TaxSettings, Unit
from apps.imports.parser import ParsedWorkbook, format_cpf, parse_workbook
from apps.payroll.calculator import TaxRates, compute_breakdown
from apps.payroll.models import ImportBatch, ServiceEntry, ServiceRole, event_key

SESSION_KEY = "import_preview"
STAGING_DIR = "imports/_staging"


# --- staging ---------------------------------------------------------------

def _workbook_to_dict(workbook: ParsedWorkbook) -> dict:
    data = asdict(workbook)
    data["row_count"] = workbook.row_count
    for sheet in data["sheets"]:
        sheet["activity_date"] = sheet["activity_date"].isoformat() if sheet["activity_date"] else ""
        for row in sheet["rows"]:
            row["net_amount"] = str(row["net_amount"])
    return data


def _stage_file(file_name: str, content: bytes) -> str:
    """Guarda os bytes enviados até a confirmação e devolve o caminho no storage.

    A sessão não carrega o arquivo (ela é serializada a cada request); carrega
    só o caminho. O que não for confirmado é apagado por `clear_preview`.
    """
    suffix = file_name[file_name.rfind(".") :] if "." in file_name else ""
    return default_storage.save(f"{STAGING_DIR}/{uuid.uuid4().hex}{suffix}", ContentFile(content))


def stage_uploads(session, uploaded_files) -> list[dict]:
    """Parses the files and stores the preview in the session. Returns per-file errors."""
    # Uma prévia nova substitui a anterior; sem apagar a antiga primeiro, os
    # arquivos dela ficariam órfãos em media/imports/_staging para sempre.
    clear_preview(session)
    workbooks, errors = [], []
    for uploaded in uploaded_files:
        content = uploaded.read()
        try:
            workbook = _workbook_to_dict(parse_workbook(uploaded.name, content))
        except Exception as error:  # noqa: BLE001 - surface any parser failure to the user
            errors.append({"file_name": uploaded.name, "message": str(error)})
            continue
        workbook["staged_path"] = _stage_file(uploaded.name, content)
        workbooks.append(workbook)
    session[SESSION_KEY] = workbooks
    return errors


def load_preview(session) -> list[dict]:
    return session.get(SESSION_KEY, [])


def clear_preview(session) -> None:
    """Descarta a prévia e apaga as planilhas que ficaram sem lote."""
    for workbook in session.get(SESSION_KEY, []):
        _discard_staged(workbook.get("staged_path"))
    session.pop(SESSION_KEY, None)


def _discard_staged(path: str | None) -> None:
    if path and default_storage.exists(path):
        default_storage.delete(path)


def _attach_source_file(batch: ImportBatch, file_name: str, staged_path: str | None) -> None:
    """Move a planilha do staging para o lote, sob o nome original."""
    if not staged_path or not default_storage.exists(staged_path):
        return
    with default_storage.open(staged_path, "rb") as staged:
        batch.source_file.save(file_name, ContentFile(staged.read()), save=True)
    default_storage.delete(staged_path)


# --- enrichment ------------------------------------------------------------

def _current_rates() -> TaxRates:
    tax = TaxSettings.current()
    return TaxRates.from_percentages(tax.inss_rate, tax.iss_rate, tax.ir_rate)


def _is_duplicate(applicator: Applicator | None, activity_date: str, event_name: str, shift: str, role: str) -> bool:
    """Aviso da prévia: esta pessoa já tem este serviço lançado?

    Olha os mesmos campos da restrição do banco menos a unidade, que ainda não
    foi escolhida — quem escolhe é o operador, nesta tela. Marcar a linha é o
    aviso; quem garante que a duplicata não entra é a restrição, e a
    confirmação pula a linha antes de tentar gravá-la.
    """
    if applicator is None or not activity_date:
        return False
    return ServiceEntry.objects.filter(
        applicator=applicator,
        activity_date=activity_date,
        event_key=event_key(event_name),
        shift=shift or "",
        role=role,
    ).exists()


def enrich_preview(workbooks: list[dict]) -> list[dict]:
    """Adds display name, match status, duplicate flag and gross amount to each row."""
    rates = _current_rates()
    for file_index, workbook in enumerate(workbooks):
        for sheet_index, sheet in enumerate(workbook["sheets"]):
            # Field-name prefixes shared with confirm_import (the template just echoes them).
            sheet["prefix"] = f"sheet-{file_index}-{sheet_index}"
            for row_index, row in enumerate(sheet["rows"]):
                row["prefix"] = f"{sheet['prefix']}-row-{row_index}"
                base_name, suffix = split_suffix(row["name"])
                applicator = Applicator.find_by_cpf(row.get("cpf", "")) or Applicator.find_by_name(base_name)
                net_amount = Decimal(row["net_amount"])
                row["display_name"] = applicator.full_name if applicator else to_display_name(base_name)
                row["suffix"] = suffix
                row["is_known"] = applicator is not None
                row["is_duplicate"] = _is_duplicate(
                    applicator, sheet["activity_date"], sheet["event_name"], sheet["shift"], row["role"]
                )
                row["gross_amount"] = str(compute_breakdown(net_amount, rates).gross_amount)
    return workbooks


# --- duplicatas de nome ----------------------------------------------------
#
# As listas escrevem a mesma pessoa de dois jeitos ("Larissa Maia" numa aba,
# "Larissa Salgado Maia" em outra) e cada grafia vira um cadastro, um RPA e uma
# linha no resumo. Juntar sozinho seria pior: "Felipe Cardoso Oliveira" e
# "Felipe Carneiro Oliveira" se parecem e podem ser duas pessoas. Então o
# sistema levanta o par e o operador decide, um a um, antes de lançar.

MERGE_FIELD_PREFIX = "merge-"
MERGE_ANSWERS = {"sim", "nao"}
# Terceira resposta da pergunta de criação: "applicator:12" lança no cadastro 12.
APPLICATOR_ANSWER = "applicator:"
SERVICES_SHOWN = 4


def _question_id(variant: str, target: str) -> str:
    """Id estável para o par: a prévia rende e a confirmação cobra o mesmo campo."""
    digest = hashlib.sha1(f"{variant}|{target}".encode()).hexdigest()
    return f"{MERGE_FIELD_PREFIX}{digest[:10]}"


def _short_date(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value or "sem data"


def _preview_names(workbooks: list[dict]) -> dict[str, dict]:
    """Nomes distintos da prévia, com os serviços de cada um (para o card mostrar)."""
    names: dict[str, dict] = {}
    for workbook in workbooks:
        for sheet in workbook["sheets"]:
            for row in sheet["rows"]:
                base, _ = split_suffix(row["name"])
                key = normalize_name(base)
                if not key:
                    continue
                entry = names.setdefault(key, {
                    "normalized": key, "raw": base, "display": to_display_name(base),
                    "services": [], "count": 0,
                })
                entry["count"] += 1
                if len(entry["services"]) < SERVICES_SHOWN:
                    entry["services"].append({
                        "date": _short_date(sheet["activity_date"]),
                        "event": sheet["event_name"],
                        "amount": row["net_amount"],
                    })
    return names


def _applicator_option(applicator: Applicator) -> dict:
    entries = ServiceEntry.objects.filter(applicator=applicator).count()
    detail = applicator.get_registration_status_display()
    if entries:
        detail += f" · {entries} lançamento(s) no sistema"
    return {
        "normalized": applicator.normalized_name, "display": applicator.full_name,
        "detail": detail, "value": f"applicator:{applicator.pk}",
        "services": [], "count": 0,
    }


def _preview_option(entry: dict) -> dict:
    return {
        "normalized": entry["normalized"], "display": entry["display"],
        "detail": f"outro nome nesta importação · {entry['count']} lançamento(s)",
        "value": f"name:{entry['display']}",
        "services": entry["services"], "count": entry["count"],
    }


def merge_questions(workbooks: list[dict]) -> list[dict]:
    """Um par de nomes parecidos por pergunta, do mais curto para o mais completo.

    Cada pergunta é feita uma vez só, mesmo que o nome apareça em várias abas:
    quem decide decide sobre a pessoa, não sobre a linha.
    """
    names = _preview_names(workbooks)
    applicators = list(Applicator.objects.all())
    by_normalized = {applicator.normalized_name: applicator for applicator in applicators}
    questions, asked = [], set()

    for key in sorted(names):
        entry = names[key]
        options = [_preview_option(names[other]) for other in names if other != key and looks_like_same_person(key, other)]
        options += [
            _applicator_option(applicator)
            for applicator in applicators
            if applicator.normalized_name != key
            and applicator.normalized_name not in names
            and looks_like_same_person(key, applicator.normalized_name)
        ]
        if not options:
            continue
        # O nome mais completo manda: juntar para trás perderia sobrenome.
        best = max(options, key=lambda option: (len(name_tokens(option["normalized"])), option["count"]))
        if len(name_tokens(best["normalized"])) < len(name_tokens(key)):
            continue  # este é o nome completo; a pergunta sai pelo lado curto
        pair = frozenset((key, best["normalized"]))
        if pair in asked:
            continue
        asked.add(pair)
        if best["value"].startswith("name:") and best["normalized"] in by_normalized:
            best = dict(best, value=f"applicator:{by_normalized[best['normalized']].pk}",
                        detail=f"já cadastrado · também nesta importação, em {best['count']} lançamento(s)")
        questions.append({
            "kind": "merge",
            "id": _question_id(key, best["value"]),
            "variant": dict(entry, detail=f"{entry['count']} lançamento(s) nesta importação",
                            known=key in by_normalized),
            "target": best,
        })
    return questions


def creation_questions(workbooks: list[dict], merges: list[dict] | None = None) -> list[dict]:
    """Um nome que não casa com ninguém: criar cadastro novo ou deixar de fora?

    A lista de aplicadores é a fonte da verdade — os nomes que estão lá foram
    conferidos. Quando a planilha traz um nome que não é nenhum deles e nem se
    parece com nenhum deles (esse caso vira pergunta de junção, não de
    criação), ninguém pode decidir sozinho se é gente nova ou erro de digitação
    de alguém que já existe. Então o sistema pergunta, e há três saídas: criar
    um cadastro novo (marcado como primeiro pagamento), deixar as linhas de
    fora, ou lançar tudo no cadastro de outra pessoa — o caso do sobrenome
    trocado, em que o nome da planilha não é ninguém novo, é alguém que já
    está lá escrito errado.
    """
    merges = merge_questions(workbooks) if merges is None else merges
    # Quem já tem pergunta de junção não recebe pergunta de criação: recusar a
    # junção ("são pessoas diferentes") já é dizer que a pessoa é nova.
    in_merge = {question["variant"]["normalized"] for question in merges}
    in_merge |= {question["target"]["normalized"] for question in merges}
    known = set(Applicator.objects.values_list("normalized_name", flat=True))
    questions = []
    for key, entry in sorted(_preview_names(workbooks).items()):
        if key in known or key in in_merge:
            continue
        questions.append({
            "kind": "create",
            "id": _question_id("criar", key),
            "variant": dict(entry, detail=f"{entry['count']} lançamento(s) nesta importação", known=False),
            "target": None,
        })
    return questions


def all_questions(workbooks: list[dict]) -> list[dict]:
    """As perguntas da prévia, na ordem em que o operador as responde."""
    merges = merge_questions(workbooks)
    return merges + creation_questions(workbooks, merges)


def read_answers(payload, workbooks: list[dict]) -> tuple[dict[str, str], set[str]]:
    """Devolve (junções confirmadas, nomes cuja criação foi recusada)."""
    merges = merge_questions(workbooks)
    answers = _read_merge_answers(payload, merges)
    declined = set()
    for question in creation_questions(workbooks, merges):
        answer = payload.get(question["id"], "")
        name = question["variant"]["display"]
        normalized = question["variant"]["normalized"]
        if answer.startswith(APPLICATOR_ANSWER):
            answers[normalized] = _validated_applicator_answer(answer, name)
            continue
        if answer not in MERGE_ANSWERS:
            raise ValueError(
                "Há cadastros novos para confirmar antes de lançar: responda a pergunta de "
                f"\u201c{name}\u201d."
            )
        if answer == "nao":
            declined.add(normalized)
    return answers, declined


def _validated_applicator_answer(answer: str, name: str) -> str:
    """Confere que o cadastro escolhido existe antes de lançar qualquer coisa nele.

    A resposta vem de um campo do formulário, então ela pode chegar com um id
    que não existe mais — alguém excluiu a ficha enquanto a prévia estava
    aberta — e o certo é parar a importação inteira e perguntar de novo, não
    estourar no meio da gravação.
    """
    _, _, pk = answer.partition(":")
    if not pk.isdigit() or not Applicator.objects.filter(pk=int(pk)).exists():
        raise ValueError(
            f"O cadastro escolhido para \u201c{name}\u201d não existe mais. Confira a resposta e tente de novo."
        )
    return answer


def _read_merge_answers(payload, questions: list[dict]) -> dict[str, str]:
    """Respostas do operador, validadas contra as perguntas que a prévia fez.

    Pergunta sem resposta interrompe a importação: o pedido é confirmar uma a
    uma, e lançar no escuro é justamente o que se quer evitar.
    """
    answers = {}
    for question in questions:
        answer = payload.get(question["id"], "")
        if answer not in MERGE_ANSWERS:
            raise ValueError(
                "Há nomes parecidos para confirmar antes de lançar: responda a pergunta de "
                f"\u201c{question['variant']['display']}\u201d."
            )
        if answer == "sim":
            answers[question["variant"]["normalized"]] = (question["target"]["normalized"], question["target"]["value"])
    return _follow_chains(answers)


def _follow_chains(answers: dict[str, tuple[str, str]]) -> dict[str, str]:
    """A ponta da corrente manda.

    "Felipe Carneiro" pode juntar em "Felipe Cardoso", que por sua vez juntou em
    "Felipe Cardoso Oliveira Costa". Sem seguir a corrente, cada resposta iria
    para um cadastro diferente e o "sim" duplo produziria a duplicata que ele
    queria desfazer. O contador de saltos corta qualquer ciclo.
    """
    merges = {}
    for variant, (target, value) in answers.items():
        seen = {variant}
        for _ in range(len(answers)):
            if target not in answers or target in seen:
                break
            seen.add(target)
            target, value = answers[target]
        merges[variant] = value
    return merges


def _resolve_merge_target(value: str, cache: dict[str, Applicator]) -> tuple[Applicator, bool]:
    """"applicator:12" -> cadastro existente; "name:Larissa Salgado Maia" -> um só cadastro por importação."""
    if value in cache:
        return cache[value], False
    kind, _, rest = value.partition(":")
    if kind == "applicator":
        applicator = Applicator.objects.get(pk=int(rest))
        created = False
    else:
        applicator, created = _get_or_create_applicator(rest, "")
    cache[value] = applicator
    return applicator, created


# --- confirmation ----------------------------------------------------------

def _get_or_create_applicator(raw_name: str, suffix: str, cpf: str = "") -> tuple[Applicator, bool]:
    """Acha a pessoa pelo CPF primeiro, pelo nome depois; cria se não existir.

    A lista de formulário traz CPF, então ela identifica melhor do que a lista
    de Lourdes: um CPF conhecido casa mesmo com o nome escrito de outro jeito.
    """
    cpf = format_cpf(cpf) if cpf else ""
    applicator = Applicator.find_by_cpf(cpf) or Applicator.find_by_name(raw_name)
    if applicator:
        if cpf and not applicator.cpf:
            applicator.cpf = cpf
            applicator.save(update_fields=["cpf", "updated_at"])
        return applicator, False
    applicator = Applicator.objects.create(
        full_name=to_display_name(raw_name),
        cpf=cpf,
        registration_status=RegistrationStatus.NEW,
        notes=f"Criado automaticamente pela importação. Sufixo na lista: {suffix}" if suffix else "Criado automaticamente pela importação.",
    )
    return applicator, True


def _amount_from(raw, fallback: Decimal = Decimal("0")) -> Decimal:
    """Lê um valor digitado ("85", "85,50", "R$ 85,50"); vazio ou inválido vira o padrão."""
    text = str(raw or "").strip().replace("R$", "").replace(" ", "")
    if not text:
        return fallback
    try:
        return Decimal(text.replace(".", "").replace(",", ".") if "," in text else text)
    except (ArithmeticError, ValueError):
        return fallback


def _read_sheet_fields(payload, prefix: str) -> dict:
    return {
        "default_amount": _amount_from(payload.get(f"{prefix}-default_amount")),
        "event_name": payload.get(f"{prefix}-event_name", "").strip(),
        "activity_date": payload.get(f"{prefix}-activity_date", ""),
        "unit_id": payload.get(f"{prefix}-unit"),
        "sector_id": payload.get(f"{prefix}-sector"),
        "shift": payload.get(f"{prefix}-shift", ""),
    }


@transaction.atomic
def confirm_import(payload, workbooks: list[dict], user) -> dict:
    """Persists the selected rows. Returns counters for the success message."""
    merges, declined = read_answers(payload, workbooks)
    merge_cache: dict[str, Applicator] = {}
    created_entries = created_applicators = skipped_rows = merged_rows = duplicate_rows = 0
    for file_index, workbook in enumerate(workbooks):
        batch = None
        for sheet_index, sheet in enumerate(workbook["sheets"]):
            prefix = f"sheet-{file_index}-{sheet_index}"
            if payload.get(f"{prefix}-include") != "on":
                continue
            fields = _read_sheet_fields(payload, prefix)
            if not fields["event_name"] or not fields["activity_date"]:
                raise ValueError(f"Aba '{sheet['sheet_name']}' de {workbook['file_name']}: informe nome da atividade e data.")
            unit = Unit.objects.get(pk=fields["unit_id"])
            sector = Sector.objects.get(pk=fields["sector_id"])
            activity_date = date.fromisoformat(fields["activity_date"])
            for row_index, row in enumerate(sheet["rows"]):
                row_prefix = f"{prefix}-row-{row_index}"
                if payload.get(f"{row_prefix}-include") != "on":
                    skipped_rows += 1
                    continue
                net_amount = _amount_from(payload.get(f"{row_prefix}-net_amount"), fallback=_amount_from(row["net_amount"]))
                if net_amount <= 0:
                    net_amount = fields["default_amount"]
                if net_amount <= 0:
                    raise ValueError(
                        f"Aba '{sheet['sheet_name']}' de {workbook['file_name']}: informe o valor por pessoa "
                        f"(a lista de formulário não traz valor)."
                    )
                role = payload.get(f"{row_prefix}-role", row["role"])
                base_name, suffix = split_suffix(row["name"])
                if normalize_name(base_name) in declined:
                    # O operador respondeu que não é para criar este cadastro:
                    # a linha fica de fora em vez de virar um aplicador solto.
                    skipped_rows += 1
                    continue
                target = merges.get(normalize_name(base_name))
                if target:
                    applicator, was_created = _resolve_merge_target(target, merge_cache)
                    merged_rows += 1
                else:
                    applicator, was_created = _get_or_create_applicator(base_name, suffix, row.get("cpf", ""))
                created_applicators += int(was_created)
                role = role if role in ServiceRole.values else ServiceRole.APPLICATOR
                if ServiceEntry.find_duplicate(
                    applicator=applicator, activity_date=activity_date, event_name=fields["event_name"],
                    shift=fields["shift"], role=role, unit=unit,
                ):
                    # Este serviço já está lançado. A lista chegou duas vezes —
                    # normalmente porque a planilha da semana é cópia da
                    # anterior e uma aba ficou com a data antiga. Gravar de novo
                    # pagaria a pessoa duas vezes pelo mesmo turno, então a
                    # linha fica de fora e entra na contagem que a mensagem de
                    # sucesso mostra. A consulta enxerga o que esta mesma
                    # importação acabou de gravar: tudo corre numa transação só.
                    #
                    # `ServiceEntry.save` recusaria a gravação de todo jeito,
                    # com `DuplicateServiceEntry`. A pergunta é feita aqui antes
                    # porque uma importação em que toda linha já existe não deve
                    # deixar para trás um lote vazio: o lote só nasce quando há
                    # o que gravar nele.
                    duplicate_rows += 1
                    continue
                if batch is None:
                    batch = ImportBatch.objects.create(file_name=workbook["file_name"], imported_by=user)
                    _attach_source_file(batch, workbook["file_name"], workbook.get("staged_path"))
                ServiceEntry.objects.create(
                    applicator=applicator,
                    role=role,
                    activity_date=activity_date,
                    event_name=fields["event_name"],
                    shift=fields["shift"],
                    sector=sector,
                    unit=unit,
                    net_amount=net_amount,
                    notes=suffix,
                    import_batch=batch,
                    created_by=user,
                )
                created_entries += 1
        if batch is None:
            _discard_staged(workbook.get("staged_path"))
    return {
        "entries": created_entries, "applicators": created_applicators,
        "skipped": skipped_rows, "merged": merged_rows, "duplicates": duplicate_rows,
    }
