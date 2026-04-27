"""Helpers para registrar log de auditoria de ações críticas.

As ações registradas são apenas as sensíveis, conforme decisão do produto:
- Criação de usuário
- Exclusão de usuário
- Mudança de papel (PerfilUsuario.papel)
- Exclusão de escola
- Reset de senha por administrador
- Desativação de usuário

NÃO registramos operações pedagógicas rotineiras (turmas/alunos/aulas/eventos)
para evitar inflar a tabela.
"""
from __future__ import annotations

from typing import Any, Optional

from django.contrib.auth.models import User


def registrar(
    autor: Optional[User],
    acao: str,
    descricao: str = "",
    *,
    recurso: str = "",
    recurso_id: Optional[int] = None,
    escola=None,
    detalhes: Optional[dict] = None,
) -> None:
    """Cria um LogAuditoria. Falha silenciosa para nunca quebrar a view."""
    try:
        from ..models import LogAuditoria
        LogAuditoria.objects.create(
            autor=autor if (autor and getattr(autor, "is_authenticated", False)) else None,
            acao=acao,
            descricao=descricao[:255],
            recurso=recurso[:50],
            recurso_id=recurso_id,
            escola=escola,
            detalhes=detalhes or {},
        )
    except Exception:
        # Auditoria nunca pode quebrar a operação principal.
        # Em produção, considere logar o erro num logger.
        import logging
        logging.getLogger(__name__).exception("Falha ao registrar auditoria")
