"""
{% avatar user "sm" %} renders someone's face as a circle, falling back to the
initials tile when the profile carries no photo. One tag so the rail, the
profile card and the import table can never drift apart.
"""
from django import template
from django.templatetags.static import static

register = template.Library()

SIZES = {"sm": "avatar--sm", "md": "", "lg": "avatar--lg", "xl": "avatar--xl"}


def _initials(name: str) -> str:
    words = [word for word in (name or "").split() if word]
    if not words:
        return "?"
    return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()


@register.inclusion_tag("core/_avatar.html")
def avatar(user, size: str = "md"):
    profile = getattr(user, "profile", None) if user is not None else None
    name = ""
    if user is not None:
        name = user.get_full_name() or user.get_username()
    photo = profile.photo if profile and profile.photo else ""
    return {
        "name": name,
        "photo": static(photo) if photo else "",
        "initials": _initials(name),
        "size_class": SIZES.get(size, ""),
    }
