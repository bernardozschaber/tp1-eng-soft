"""Data for the left sidebar: open totals grouped by unit or paying company."""
from django.db.models import Count, Sum
from django.urls import reverse

from apps.payroll.models import ServiceEntry


def build_sidebar(mode: str) -> dict:
    """Returns {"mode", "groups": [{name, total, count, url}]} for all entries."""
    if mode == "companies":
        name_field, filter_key = "paying_company__name", "company"
    else:
        mode, name_field, filter_key = "units", "unit__name", "unit"
    rows = (
        ServiceEntry.objects.values(name_field, f"{filter_key}_id" if filter_key == "unit" else "paying_company_id")
        .annotate(total=Sum("net_amount"), count=Count("id"))
        .order_by("-total")
    )
    groups = []
    for row in rows:
        group_id = row["unit_id"] if filter_key == "unit" else row["paying_company_id"]
        groups.append(
            {
                "name": row[name_field],
                "total": row["total"],
                "count": row["count"],
                "url": f"{reverse('payroll:entry_list')}?{filter_key}={group_id}",
            }
        )
    return {"mode": mode, "groups": groups}
