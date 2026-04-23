"""Helpers de papéis e escopo (escola/professor) para todo o sistema.

Hierarquia de papéis (ordem decrescente de poder):

    superadmin       → vê e administra TUDO de todas as escolas
                       (papel='superadmin' OU is_superuser/is_staff do Django)

    admin_escola     → administra TUDO dentro das escolas vinculadas ao perfil
    coordenador      → mesmas permissões do admin_escola (alias)

    professor        → vê/edita SOMENTE as próprias aulas/diários

    aluno            → vê tarefas/horário/diário da própria turma
    responsavel      → vê tarefas/horário/diário dos filhos vinculados
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from ..models import (
    Escola, Turma, Professor, Materia, Livro, Aula, Aluno, AgendaEvento,
    Horario, PerfilUsuario,
)


# ── Identidade / Papel ─────────────────────────────────────────────────────

def _perfil(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil", None)


def papel_de(user):
    """Retorna o papel string do usuário ('superadmin', 'admin_escola', ...) ou None."""
    perfil = _perfil(user)
    if perfil:
        return perfil.papel
    if user and user.is_authenticated and (user.is_superuser or user.is_staff):
        return PerfilUsuario.PAPEL_SUPERADMIN
    return None


def is_superadmin(user):
    """Vê e administra TUDO. Superuser/staff do Django também são tratados como superadmin."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    perfil = _perfil(user)
    return bool(perfil and perfil.papel == PerfilUsuario.PAPEL_SUPERADMIN)


def is_admin_escola(user):
    """Administrador de escola (inclui coordenador e superadmin)."""
    if is_superadmin(user):
        return True
    perfil = _perfil(user)
    return bool(perfil and perfil.papel in (
        PerfilUsuario.PAPEL_ADMIN_ESCOLA,
        PerfilUsuario.PAPEL_COORDENADOR,
    ))


def is_coordenador(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.papel == PerfilUsuario.PAPEL_COORDENADOR)


def is_professor(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.papel == PerfilUsuario.PAPEL_PROFESSOR)


def is_aluno(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.papel == PerfilUsuario.PAPEL_ALUNO)


def is_responsavel(user):
    perfil = _perfil(user)
    return bool(perfil and perfil.papel == PerfilUsuario.PAPEL_RESPONSAVEL)


def professor_do_usuario(user):
    """Retorna o Professor vinculado ao usuário (ou None).

    Fonte oficial: ProfessorUsuario (ativo=True) — o campo
    PerfilUsuario.professor_vinculado é apenas um cache mantido em sincronia
    pelos sinais em `agenda/signals.py`. Sem fallback silencioso: se o
    cache estiver vazio, é porque não há vínculo ativo.
    """
    if not user or not user.is_authenticated:
        return None
    perfil = _perfil(user)
    return perfil.professor_vinculado if perfil else None


# ── Helpers para Aluno / Responsável / Professor (escopo pedagógico) ───────

def alunos_do_consumidor(user):
    """Alunos vinculados ao usuário (próprio aluno OU filhos do responsável)."""
    if user is None or not user.is_authenticated:
        return Aluno.objects.none()
    return Aluno.objects.filter(usuarios=user).distinct()


def turmas_do_aluno(user):
    """Turmas dos alunos vinculados ao usuário (aluno ou responsável)."""
    return Turma.objects.filter(aluno__usuarios=user).distinct()


def turmas_do_professor(user):
    """Turmas onde o professor leciona (via Horario)."""
    prof = professor_do_usuario(user)
    if not prof:
        return Turma.objects.none()
    return Turma.objects.filter(horarios__professor=prof).distinct()


def materias_do_professor(user):
    """Matérias do professor (via Horario + matéria principal do Professor)."""
    prof = professor_do_usuario(user)
    if not prof:
        return Materia.objects.none()
    ids = set(
        Horario.objects.filter(professor=prof)
        .values_list("materia_id", flat=True)
    )
    if prof.materia_id:
        ids.add(prof.materia_id)
    return Materia.objects.filter(id__in=ids)


# ── Escolas: visíveis vs administradas ─────────────────────────────────────

def escolas_do_usuario(user):
    """Escolas que o usuário pode VER (queryset)."""
    perfil = _perfil(user)
    if perfil is None:
        # Usuário sem perfil: tratamos como superadmin de fato (compat: staff/superuser)
        return Escola.objects.all() if (user and user.is_authenticated and (user.is_superuser or user.is_staff)) else Escola.objects.none()
    if perfil.papel == PerfilUsuario.PAPEL_SUPERADMIN or user.is_superuser or user.is_staff:
        return Escola.objects.all()
    return perfil.escolas_visiveis()


def escolas_administradas(user):
    """Escolas onde o usuário tem poder ADMIN (CRUD de turmas/alunos/professores etc)."""
    if is_superadmin(user):
        return Escola.objects.all()
    if not is_admin_escola(user):
        return Escola.objects.none()
    return _perfil(user).escolas_visiveis()


def pode_administrar_escola(user, escola):
    """True se o user pode administrar conteúdo dessa escola."""
    if is_superadmin(user):
        return True
    if not is_admin_escola(user) or escola is None:
        return False
    return escolas_administradas(user).filter(pk=escola.pk if hasattr(escola, "pk") else escola).exists()


# ── Querysets escopo escola ────────────────────────────────────────────────

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


# ── Filtro genérico por escola para LIST views ─────────────────────────────

def filtrar_por_escola(qs, user, escola_lookup="escola"):
    """Filtra `qs` para conter apenas registros das escolas administradas.

    - superadmin → qs intacto
    - admin_escola → qs filtrado por <escola_lookup>__in=escolas_administradas(user)
    - outros → qs.none()
    """
    if is_superadmin(user):
        return qs
    if is_admin_escola(user):
        return qs.filter(**{f"{escola_lookup}__in": escolas_administradas(user)})
    return qs.none()


# ── Aulas (escopo professor + admin_escola) ────────────────────────────────

def aulas_do_usuario(user, base_qs=None):
    """Aulas visíveis ao usuário.

    - superadmin → todas
    - admin_escola/coordenador → todas das escolas administradas
    - professor → próprias OU das matérias/turmas onde leciona
    - aluno/responsável → das turmas do(s) aluno(s) (somente leitura)
    - outros → nada
    """
    from django.db.models import Q
    qs = base_qs if base_qs is not None else Aula.objects.all()
    if is_superadmin(user):
        return qs
    if is_admin_escola(user):
        return qs.filter(escola__in=escolas_administradas(user))
    if is_professor(user):
        prof = professor_do_usuario(user)
        if not prof:
            return qs.none()
        turmas_ids = list(turmas_do_professor(user).values_list("id", flat=True))
        materias_ids = list(materias_do_professor(user).values_list("id", flat=True))
        return qs.filter(
            Q(professor=prof)
            | (Q(turma_id__in=turmas_ids) & Q(materia_id__in=materias_ids))
        ).distinct()
    if is_aluno(user) or is_responsavel(user):
        return qs.filter(turma__in=turmas_do_aluno(user))
    return qs.none()


def pode_editar_aula(user, aula):
    """True se o user pode editar/excluir esta aula."""
    if is_superadmin(user):
        return True
    if is_admin_escola(user):
        return escolas_administradas(user).filter(pk=aula.escola_id).exists()
    if is_professor(user):
        prof = professor_do_usuario(user)
        if not prof:
            return False
        if aula.professor_id == prof.id:
            return True
        # Aulas das turmas/matérias dele
        return Horario.objects.filter(
            professor=prof, turma_id=aula.turma_id, materia_id=aula.materia_id
        ).exists()
    return False


# ── Eventos da Agenda ──────────────────────────────────────────────────────

def eventos_do_usuario(user, base_qs=None):
    """Eventos visíveis ao usuário.

    - superadmin → todos
    - admin_escola/coordenador → das escolas administradas
    - professor → tudo das escolas visíveis (leitura ampla)
    - aluno/responsável → apenas das turmas vinculadas ao(s) aluno(s)
    """
    qs = base_qs if base_qs is not None else AgendaEvento.objects.all()
    if is_superadmin(user):
        return qs
    if is_admin_escola(user):
        return qs.filter(turma__escola__in=escolas_administradas(user))
    if is_professor(user):
        return qs.filter(turma__escola__in=escolas_do_usuario(user))
    if is_aluno(user) or is_responsavel(user):
        return qs.filter(turma__in=turmas_do_aluno(user))
    return qs.none()


def pode_editar_evento(user, evento):
    """Quem pode editar/excluir um evento da agenda.

    - superadmin/admin_escola → sim (dentro do escopo)
    - professor → só os eventos manuais que ele criou (evento.professor == ele)
    - aluno/responsável → não
    """
    if is_superadmin(user):
        return True
    if is_admin_escola(user):
        escola_id = evento.escola_id or (evento.turma.escola_id if evento.turma_id else None)
        if escola_id is None:
            return True
        return escolas_administradas(user).filter(pk=escola_id).exists()
    if is_professor(user):
        prof = professor_do_usuario(user)
        return bool(prof and evento.professor_id == prof.id)
    return False


# ── Horários (visíveis em modo leitura para todos os logados) ──────────────

def horarios_do_usuario(user, base_qs=None):
    """Horários visíveis (leitura).

    - superadmin → todos
    - admin_escola/coordenador → das escolas administradas
    - professor → todos das escolas visíveis
    - aluno/responsável → apenas das turmas vinculadas
    """
    from .. import models as _m
    qs = base_qs if base_qs is not None else _m.Horario.objects.all()
    if is_superadmin(user):
        return qs
    if is_admin_escola(user):
        return qs.filter(turma__escola__in=escolas_administradas(user))
    if is_professor(user):
        return qs.filter(turma__escola__in=escolas_do_usuario(user))
    if is_aluno(user) or is_responsavel(user):
        return qs.filter(turma__in=turmas_do_aluno(user))
    return qs.none()


# ── Form helpers ───────────────────────────────────────────────────────────

def aplicar_escopo_no_form(form, user):
    """Aplica filtros de escola/perfil aos campos cascata de um ModelForm."""
    fields = form.fields
    if "escola" in fields:
        # admin_escola só pode salvar em suas escolas administradas
        if is_admin_escola(user) and not is_superadmin(user):
            fields["escola"].queryset = escolas_administradas(user)
        else:
            fields["escola"].queryset = escolas_do_usuario(user)
    if "turma" in fields:
        fields["turma"].queryset = turmas_do_usuario(user)
    if "professor" in fields:
        fields["professor"].queryset = professores_do_usuario(user)
    if "materia" in fields:
        fields["materia"].queryset = materias_do_usuario(user)
    if "livro" in fields:
        fields["livro"].queryset = livros_do_usuario(user)

    perfil = _perfil(user)

    # Trava o campo "professor" para PROFESSOR comum (admin_escola e superadmin podem mudar)
    if (
        "professor" in fields
        and not is_admin_escola(user)
        and perfil
        and perfil.professor_vinculado_id
    ):
        prof = perfil.professor_vinculado
        fields["professor"].queryset = Professor.objects.filter(pk=prof.id)
        fields["professor"].initial = prof.id
        fields["professor"].disabled = True
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


# ── Decorators ─────────────────────────────────────────────────────────────

def _negar(request, mensagem):
    messages.error(request, mensagem)
    return redirect("cal:home")


def admin_escola_required(view_func):
    """Permite acesso a admin_escola, coordenador e superadmin."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not is_admin_escola(request.user):
            return _negar(request, "Você não tem permissão para acessar esta página.")
        return view_func(request, *args, **kwargs)
    return wrapped


def admin_estrito_required(view_func):
    """Permite somente Administrador da Escola (admin_escola) e Super-admin.
    Coordenador NÃO tem acesso (use admin_escola_required para incluir coordenador)."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not (is_superadmin(request.user) or papel_de(request.user) == PerfilUsuario.PAPEL_ADMIN_ESCOLA):
            return _negar(request, "Apenas Administrador da Escola pode acessar esta área.")
        return view_func(request, *args, **kwargs)
    return wrapped


def superadmin_required(view_func):
    """Permite acesso somente ao super-administrador (configurações globais)."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not is_superadmin(request.user):
            return _negar(request, "Esta área é restrita ao super-administrador.")
        return view_func(request, *args, **kwargs)
    return wrapped


def bloquear_alunos_responsaveis(view_func):
    """Bloqueia alunos e responsáveis (qualquer outro papel passa)."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if is_aluno(request.user) or is_responsavel(request.user):
            return _negar(request, "Esta área é restrita à equipe pedagógica.")
        return view_func(request, *args, **kwargs)
    return wrapped


def professor_ou_admin_required(view_func):
    """Permite professor, coordenador, admin_escola e superadmin."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not (is_professor(request.user) or is_admin_escola(request.user)):
            return _negar(request, "Esta área é restrita a professores e administradores.")
        return view_func(request, *args, **kwargs)
    return wrapped


def papel_required(*papeis):
    """Decorator que aceita uma lista de papéis permitidos."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if papel_de(request.user) not in papeis and not is_superadmin(request.user):
                return _negar(request, "Você não tem permissão para acessar esta página.")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
