"""Helpers para restringir querysets ao escopo (escola/professor) do usuário logado."""

from ..models import Escola, Turma, Professor, Materia, Livro, Aula


# ── Identidade ─────────────────────────────────────────────────────────────

def is_admin(user):
    """Usuários com poderes administrativos (veem e editam tudo)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    perfil = getattr(user, "perfil", None)
    return bool(perfil and perfil.is_admin_escola)


def professor_do_usuario(user):
    """Retorna o Professor vinculado ao user logado (ou None)."""
    if not user or not user.is_authenticated:
        return None
    perfil = getattr(user, "perfil", None)
    return perfil.professor_vinculado if perfil else None


# ── Querysets escopo escola ────────────────────────────────────────────────

def escolas_do_usuario(user):
    perfil = getattr(user, "perfil", None) if user and user.is_authenticated else None
    if perfil is None:
        return Escola.objects.all()
    return perfil.escolas_visiveis()


def turmas_do_usuario(user):
    return Turma.objects.filter(escola__in=escolas_do_usuario(user))


def professores_do_usuario(user):
    return Professor.objects.filter(escola__in=escolas_do_usuario(user))


def materias_do_usuario(user):
    """Matérias acessíveis: as que têm professores nas escolas do usuário."""
    return Materia.objects.filter(
        professores__escola__in=escolas_do_usuario(user)
    ).distinct()


def livros_do_usuario(user):
    return Livro.objects.filter(escola__in=escolas_do_usuario(user))


# ── Querysets escopo professor ─────────────────────────────────────────────

def aulas_do_usuario(user, base_qs=None):
    """Aulas que o usuário pode visualizar.

    - Admin: todas (dentro das escolas visíveis).
    - Professor com vínculo: apenas as que ele criou (filtradas por professor).
    - Demais: nada (segurança por padrão).
    """
    qs = base_qs if base_qs is not None else Aula.objects.all()
    if is_admin(user):
        return qs.filter(escola__in=escolas_do_usuario(user))
    prof = professor_do_usuario(user)
    if prof is not None:
        return qs.filter(professor=prof)
    return qs.none()


def pode_editar_aula(user, aula):
    """True se o usuário pode editar/excluir esta aula específica."""
    if is_admin(user):
        return True
    prof = professor_do_usuario(user)
    return prof is not None and aula.professor_id == prof.id


# ── Form helpers ───────────────────────────────────────────────────────────

def aplicar_escopo_no_form(form, user):
    """Aplica os filtros de escola/perfil aos campos cascata de um ModelForm."""
    fields = form.fields
    if "escola" in fields:
        fields["escola"].queryset = escolas_do_usuario(user)
    if "turma" in fields:
        fields["turma"].queryset = turmas_do_usuario(user)
    if "professor" in fields:
        fields["professor"].queryset = professores_do_usuario(user)
    if "materia" in fields:
        fields["materia"].queryset = materias_do_usuario(user)
    if "livro" in fields:
        fields["livro"].queryset = livros_do_usuario(user)

    # Defaults inteligentes baseados no perfil
    perfil = getattr(user, "perfil", None) if user and user.is_authenticated else None

    # Trava o campo "professor" para não-admin com vínculo (só admin pode mudar)
    if (
        "professor" in fields
        and not is_admin(user)
        and perfil
        and perfil.professor_vinculado_id
    ):
        prof = perfil.professor_vinculado
        fields["professor"].queryset = Professor.objects.filter(pk=prof.id)
        fields["professor"].initial = prof.id
        fields["professor"].disabled = True   # ignora POST e mantém initial
        fields["professor"].empty_label = None
        fields["professor"].help_text = "Apenas o administrador pode alterar este campo."
        fields["professor"].widget.attrs["title"] = "Bloqueado: apenas administradores podem alterar."

    if perfil is None or form.is_bound or form.instance.pk:
        return

    if perfil.escola_id and "escola" in fields and not form.initial.get("escola"):
        form.initial["escola"] = perfil.escola_id

    if perfil.professor_vinculado_id and "professor" in fields and not form.initial.get("professor"):
        prof = perfil.professor_vinculado
        form.initial["professor"] = prof.id
        if "materia" in fields and prof.materia_id and not form.initial.get("materia"):
            form.initial["materia"] = prof.materia_id
        if "escola" in fields and prof.escola_id and not form.initial.get("escola"):
            form.initial["escola"] = prof.escola_id
