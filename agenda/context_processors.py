"""Disponibiliza, em todos os templates, dados úteis sobre o usuário/escola/papel."""

from .models import Escola
from .services.escopo import (
    is_superadmin, is_admin_escola, is_coordenador,
    is_professor, is_aluno, is_responsavel,
    escolas_administradas, papel_de,
)


def escola_atual(request):
    """Injeta dados do perfil/escola/papel em todos os templates."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "escola_atual": None,
            "escolas_visiveis": Escola.objects.none(),
            "perfil_usuario": None,
            "papel_usuario": None,
            "is_superadmin": False,
            "is_admin_escola": False,
            "is_coordenador": False,
            "is_professor": False,
            "is_aluno": False,
            "is_responsavel": False,
            "escolas_administradas": Escola.objects.none(),
        }

    perfil = getattr(user, "perfil", None)
    if perfil is None:
        # Sem perfil: aplicamos heurística (staff/superuser ⇒ superadmin)
        return {
            "escola_atual": None,
            "escolas_visiveis": Escola.objects.all(),
            "perfil_usuario": None,
            "papel_usuario": papel_de(user),
            "is_superadmin": is_superadmin(user),
            "is_admin_escola": is_admin_escola(user),
            "is_coordenador": False,
            "is_professor": False,
            "is_aluno": False,
            "is_responsavel": False,
            "escolas_administradas": escolas_administradas(user),
        }

    return {
        "escola_atual": perfil.escola,
        "escolas_visiveis": perfil.escolas_visiveis(),
        "perfil_usuario": perfil,
        "papel_usuario": perfil.papel,
        "is_superadmin": is_superadmin(user),
        "is_admin_escola": is_admin_escola(user),
        "is_coordenador": is_coordenador(user),
        "is_professor": is_professor(user),
        "is_aluno": is_aluno(user),
        "is_responsavel": is_responsavel(user),
        "escolas_administradas": escolas_administradas(user),
    }
