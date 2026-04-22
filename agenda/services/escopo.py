"""Helpers para restringir querysets ao escopo (escola) do usuário logado."""

from ..models import Escola, Turma, Professor, Materia, Livro


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
