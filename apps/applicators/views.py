"""Applicator registry: list with search, create, edit and detail with history."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.applicators.forms import ApplicatorForm
from apps.applicators.models import Applicator, RegistrationStatus

PAGE_SIZE = 50


@login_required
def applicator_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    queryset = Applicator.objects.order_by("full_name")
    if query:
        queryset = queryset.filter(Q(full_name__icontains=query) | Q(cpf__icontains=query) | Q(email__icontains=query))
    if status in RegistrationStatus.values:
        queryset = queryset.filter(registration_status=status)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "page": page,
        "query": query,
        "status": status,
        "new_count": Applicator.objects.filter(registration_status=RegistrationStatus.NEW).count(),
        "active_count": Applicator.objects.filter(registration_status=RegistrationStatus.ACTIVE).count(),
    }
    return render(request, "applicators/list.html", context)


@login_required
def applicator_create(request):
    form = ApplicatorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        applicator = form.save()
        messages.success(request, f"Aplicador {applicator} cadastrado.")
        return redirect("applicators:detail", pk=applicator.pk)
    return render(request, "applicators/form.html", {"form": form, "title": "Novo aplicador"})


@login_required
def applicator_update(request, pk: int):
    applicator = get_object_or_404(Applicator, pk=pk)
    form = ApplicatorForm(request.POST or None, instance=applicator)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro atualizado.")
        return redirect("applicators:detail", pk=applicator.pk)
    return render(request, "applicators/form.html", {"form": form, "applicator": applicator, "title": "Editar aplicador"})


@login_required
def applicator_card(request, pk: int):
    """A ficha da pessoa como um cartão no meio da tela, com espaço para a foto 3x4.

    É a mesma ficha que a planilha de agendamento guarda — documentos, banco,
    curso — que não cabe na lista (lá ficam só nome, CPF, WhatsApp, e-mail e
    situação) mas é o que alguém precisa ver antes de pagar.
    """
    applicator = get_object_or_404(Applicator, pk=pk)
    return render(request, "applicators/card.html", {"applicator": applicator})


@login_required
@require_POST
def applicator_delete(request, pk: int):
    """Apaga a ficha inteira. Recusa quem já tem lançamento.

    `ServiceEntry.applicator` é PROTECT de propósito: um pagamento sem a pessoa
    a quem ele foi pago não é um registro, é um buraco. Quem já recebeu sai de
    circulação pelo "inativo", não pela exclusão.
    """
    applicator = get_object_or_404(Applicator, pk=pk)
    name = applicator.full_name
    try:
        applicator.delete()
    except ProtectedError:
        count = applicator.entries.count()
        messages.error(
            request,
            f"{name} tem {count} lançamento(s) e não pode ser excluído(a). "
            "Apague os lançamentos ou marque o cadastro como inativo.",
        )
        return redirect("applicators:card", pk=pk)
    messages.success(request, f"Ficha de {name} excluída.")
    return redirect("applicators:list")


@login_required
def applicator_detail(request, pk: int):
    applicator = get_object_or_404(Applicator, pk=pk)
    entries = applicator.entries.select_related("unit", "paying_company").order_by("-activity_date")
    totals = entries.aggregate(net=Sum("net_amount"), gross=Sum("gross_amount"), count=Count("id"))
    return render(request, "applicators/detail.html", {"applicator": applicator, "entries": entries[:100], "totals": totals})
