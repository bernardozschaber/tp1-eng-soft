"""Quem pode ver o quê: a mesma chave de seção que marca o menu (ver
`context_processors.NAV_ITEMS`) decide o que o cargo enxerga e o que a
URL direta recusa — um lugar só, para o menu e o bloqueio nunca discordarem.
"""

FULL_ACCESS_GROUP = "Acesso total"
# Seção -> grupo que a acessa. Quem não está em nenhum desses grupos (nem no
# de acesso total) só vê "Início", que não é seção de ninguém.
SECTION_GROUPS = {
    "applicators": "Administrador financeiro",
    "imports": "Usuário do RH",
    "payroll": "Gestor financeiro",
    "summary": "Gestor financeiro",
    "settings": "Gestor financeiro",
}


def section_for_view(app_name: str, view_name: str) -> str:
    """A seção da página atual, ou "" para o que é de todo mundo (Início, perfil, admin)."""
    if view_name.startswith("payroll:summary"):
        return "summary"
    if app_name == "payroll":
        return "payroll"
    if app_name == "catalog":
        return "settings"
    if app_name in ("imports", "applicators"):
        return app_name
    return ""


def allowed_sections(user) -> set[str]:
    """As seções que este usuário pode ver — todas, para quem tem acesso total."""
    if not user.is_authenticated:
        return set()
    if user.is_superuser or user.groups.filter(name=FULL_ACCESS_GROUP).exists():
        return set(SECTION_GROUPS)
    group_names = set(user.groups.values_list("name", flat=True))
    return {section for section, group in SECTION_GROUPS.items() if group in group_names}
