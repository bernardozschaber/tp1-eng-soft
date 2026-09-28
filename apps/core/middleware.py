"""Barra quem entra direto pela URL numa área que o cargo não vê no menu."""
from django.contrib import messages
from django.shortcuts import redirect

from apps.core.access import allowed_sections, section_for_view


class SectionAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if not request.user.is_authenticated or match is None:
            return None
        section = section_for_view(match.app_name or "", match.view_name or "")
        if section and section not in allowed_sections(request.user):
            messages.error(request, "Seu acesso não inclui esta área.")
            return redirect("dashboard")
        return None
