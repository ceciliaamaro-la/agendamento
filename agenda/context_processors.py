"""Disponibiliza, em todos os templates, dados úteis sobre o usuário/escola."""

from .models import Escola


def escola_atual(request):
    """Injeta `escola_atual` e `escolas_visiveis` no contexto.

    - escola_atual: a escola padrão do perfil do usuário (ou None).
    - escolas_visiveis: queryset com todas as escolas que o usuário pode ver.
    - perfil_usuario: shortcut para o PerfilUsuario.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "escola_atual": None,
            "escolas_visiveis": Escola.objects.none(),
            "perfil_usuario": None,
        }

    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return {
            "escola_atual": None,
            "escolas_visiveis": Escola.objects.all(),
            "perfil_usuario": None,
        }

    return {
        "escola_atual": perfil.escola,
        "escolas_visiveis": perfil.escolas_visiveis(),
        "perfil_usuario": perfil,
    }
