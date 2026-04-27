"""Endpoints AJAX para preenchimento em cascata dos formulários de Aula/Evento.

Selecionar um campo (Professor, Turma ou Matéria) preenche automaticamente
os demais conforme as ForeignKeys cadastradas, sempre **respeitando o escopo
de escolas do usuário logado** (PerfilUsuario.escolas_visiveis).
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from django.db.models import Q

from ..models import Professor, Turma, Materia, Livro, OrdemHorario
from ..services.escopo import escolas_do_usuario


def _opt(qs, label_attr):
    return [{"id": obj.id, "text": getattr(obj, label_attr)} for obj in qs]


@login_required
@require_GET
def cascade_professor(request, pk):
    """Dado um professor, devolve escola, matéria(s) e turmas vinculadas."""
    escolas_ids = list(escolas_do_usuario(request.user).values_list("id", flat=True))
    try:
        prof = Professor.objects.select_related("escola", "materia").get(
            pk=pk, escola_id__in=escolas_ids
        )
    except Professor.DoesNotExist:
        return JsonResponse({"ok": False}, status=404)

    materias = Materia.objects.filter(professores__id=prof.id).distinct()

    # Turmas: todas as turmas da escola do professor (assim turmas novas,
    # ainda sem horário cadastrado para este prof, também aparecem).
    turmas = Turma.objects.filter(escola_id=prof.escola_id)

    livros = Livro.objects.filter(escola_id=prof.escola_id, materia_id=prof.materia_id)

    return JsonResponse({
        "ok": True,
        "escola": {"id": prof.escola_id, "text": prof.escola.nome_escola or ""},
        "materia_default": prof.materia_id,
        "livro_default": livros.first().id if livros.count() == 1 else None,
        "materias": _opt(materias, "nome_materia"),
        "turmas": _opt(turmas, "nome_turma"),
        "livros": _opt(livros, "nome_livro"),
    })


@login_required
@require_GET
def cascade_turma(request, pk):
    """Dada uma turma, devolve escola e os professores/matérias vinculadas pelos horários."""
    escolas_ids = list(escolas_do_usuario(request.user).values_list("id", flat=True))
    try:
        turma = Turma.objects.select_related("escola").get(
            pk=pk, escola_id__in=escolas_ids
        )
    except Turma.DoesNotExist:
        return JsonResponse({"ok": False}, status=404)

    # Professores: TODOS os professores da escola da turma (independentemente
    # de já terem horários cadastrados nessa turma).
    if turma.escola_id:
        professores = Professor.objects.filter(escola_id=turma.escola_id)
    else:
        professores = Professor.objects.none()

    # Matérias: todas as matérias dos professores da escola
    if turma.escola_id:
        materias = Materia.objects.filter(
            professores__escola_id=turma.escola_id
        ).distinct()
    else:
        materias = Materia.objects.none()

    # Períodos (ordens) compatíveis: da escola da turma OU globais (escola=None),
    # respeitando o turno da turma (turno igual ou vazio = comum)
    ordens_qs = OrdemHorario.objects.filter(
        Q(escola_id=turma.escola_id) | Q(escola__isnull=True)
    )
    if turma.turno:
        ordens_qs = ordens_qs.filter(Q(turno=turma.turno) | Q(turno=""))
    ordens_qs = ordens_qs.order_by("escola__nome_escola", "turno", "posicao", "id")
    ordens = [{"id": o.id, "text": str(o)} for o in ordens_qs]

    return JsonResponse({
        "ok": True,
        "escola": {
            "id": turma.escola_id,
            "text": turma.escola.nome_escola if turma.escola else "",
        },
        "professores": _opt(professores, "nome_professor"),
        "materias": _opt(materias, "nome_materia"),
        "ordens": ordens,
        "turno": turma.turno,
    })


@login_required
@require_GET
def cascade_materia(request, pk):
    """Dada uma matéria (e opcionalmente escola), devolve professores e livros."""
    escolas_ids = list(escolas_do_usuario(request.user).values_list("id", flat=True))
    escola_id = request.GET.get("escola") or None
    professores = Professor.objects.filter(materia_id=pk, escola_id__in=escolas_ids)
    livros = Livro.objects.filter(materia_id=pk, escola_id__in=escolas_ids)
    if escola_id:
        professores = professores.filter(escola_id=escola_id)
        livros = livros.filter(escola_id=escola_id)
    professores = professores.distinct()
    livros = livros.distinct()
    return JsonResponse({
        "ok": True,
        "professores": _opt(professores, "nome_professor"),
        "livros": _opt(livros, "nome_livro"),
        "livro_default": livros.first().id if livros.count() == 1 else None,
    })
