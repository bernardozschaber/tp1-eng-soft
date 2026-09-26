"""Dashboard and static pages."""
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.payroll.dashboard import DashboardPeriod, build_dashboard


@login_required
def dashboard(request):
    period = DashboardPeriod.from_key(request.GET.get("period"))
    context = build_dashboard(period)
    context["periods"] = DashboardPeriod.options()
    context["series_json"] = json.dumps(context["series"])
    return render(request, "core/dashboard.html", context)


@login_required
def help_page(request):
    return render(request, "core/help.html")
