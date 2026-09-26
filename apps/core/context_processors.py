"""Injects the icon navigation items and sidebar data into every template."""
from django.urls import reverse

from apps.payroll.sidebar import build_sidebar

NAV_ITEMS = [
    # (label, url name, icon, app_name that marks it active)
    ("Início", "dashboard", "pie-chart", ""),
    ("Lançamentos", "payroll:entry_list", "list", "payroll"),
    ("Importar", "imports:upload", "upload", "imports"),
    ("Resumo", "payroll:summary", "file-text", "summary"),
    ("Aplicadores", "applicators:list", "users", "applicators"),
    ("Configurações", "catalog:settings", "settings", "catalog"),
]


def _is_active(app_name: str, current_app: str, view_name: str) -> bool:
    is_summary_view = view_name.startswith("payroll:summary")
    if app_name == "summary":
        return is_summary_view
    if app_name == "payroll":
        return current_app == "payroll" and not is_summary_view
    return current_app == app_name


def navigation(request):
    if not request.user.is_authenticated or request.resolver_match is None:
        return {}
    current_app = request.resolver_match.app_name or ""
    view_name = request.resolver_match.view_name or ""
    nav_items = [
        {"label": label, "url": reverse(url_name), "icon": icon_name, "active": _is_active(app_name, current_app, view_name)}
        for label, url_name, icon_name, app_name in NAV_ITEMS
    ]
    return {"nav_items": nav_items, "sidebar": build_sidebar(request.GET.get("sidebar", "units"))}
