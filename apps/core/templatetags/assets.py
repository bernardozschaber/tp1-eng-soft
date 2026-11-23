"""
{% static_v "css/app.css" %} devolve a URL do arquivo com a data de modificação
no fim (?v=1789...). Sem isso o navegador segura o CSS antigo em cache e uma
correção de estilo simplesmente não aparece — o projeto não tem build, então o
carimbo de mtime é o que faz as vezes de versão.
"""
import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(path: str) -> str:
    url = static(path)
    found = finders.find(path)
    if not found:
        return url
    try:
        stamp = int(os.path.getmtime(found))
    except OSError:
        return url
    return f"{url}?v={stamp}"
