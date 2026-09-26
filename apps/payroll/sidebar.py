"""Data for the left sidebar: open totals per unit."""
from django.db.models import Count, Sum
from django.urls import reverse

from apps.payroll.models import ServiceEntry

def build_sidebar() -> dict:
    """
    Returns {"groups": [{name, company, total, count, url}]} for all entries.

    Each unit answers to exactly one paying company ("Lourdes" is "RRPM Matriz"),
    so both live in a single list instead of two tabs.
    """
    rows = (
        ServiceEntry.objects.values("unit_id", "unit__name", "paying_company__name")        .annotate(total=Sum("net_amount"), count=Count("id"))
        .annotate(total=Sum("net_amount"), count=Count("id"))
        .order_by("-total")
    )
    groups = [
        {
            "name": row["unit__name"],
            "company": row["paying_company__name"],
            "total": row["total"],
            "count": row["count"],
            "url": f"{reverse('payroll:entry_list')}?unit={row['unit_id']}",
        }
        for row in rows
    ]
    return {"groups": groups}