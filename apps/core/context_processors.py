"""Injects the icon navigation items into every template — só as que o cargo vê."""
from django.urls import reverse

from apps.core.access import allowed_sections

NAV_ITEMS = [
    # (label, url name, icon, seção — "" é de todo mundo, ver apps.core.access)
    ("Início", "dashboard", "pie-chart", ""),
    ("Lançamentos", "payroll:entry_list", "list", "payroll"),
    ("Importar", "imports:upload", "upload", "imports"),
    ("Resumo", "payroll:summary", "file-text", "summary"),
    ("Aplicadores", "applicators:list", "users", "applicators"),
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
    sections = allowed_sections(request.user)
    nav_items = [
        {"label": label, "url": reverse(url_name), "icon": icon_name, "active": _is_active(app_name, current_app, view_name)}
        for label, url_name, icon_name, app_name in NAV_ITEMS
        if not app_name or app_name in sections
    ]
    return {"nav_items": nav_items}