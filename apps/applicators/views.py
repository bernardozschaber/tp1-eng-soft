"""Applicator registry: list with search, create, edit and detail with history."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.applicators.forms import ApplicatorForm
from apps.applicators.models import Applicator

PAGE_SIZE = 50


@login_required
def applicator_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    queryset = Applicator.objects.annotate(entry_count=Count("entries"), net_total=Sum("entries__net_amount")).order_by("full_name")
    if query:
        queryset = queryset.filter(Q(full_name__icontains=query) | Q(cpf__icontains=query) | Q(email__icontains=query))
    if status == "review":
        queryset = queryset.filter(needs_review=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {"page": page, "query": query, "status": status, "review_count": Applicator.objects.filter(needs_review=True).count()}
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
def applicator_detail(request, pk: int):
    applicator = get_object_or_404(Applicator, pk=pk)
    entries = applicator.entries.select_related("unit", "paying_company").order_by("-activity_date")
    totals = entries.aggregate(net=Sum("net_amount"), gross=Sum("gross_amount"), count=Count("id"))
    return render(request, "applicators/detail.html", {"applicator": applicator, "entries": entries[:100], "totals": totals})
