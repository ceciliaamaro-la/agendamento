"""Endpoints AJAX para preenchimento em cascata dos formulários de Aula/Evento.

Permite que selecionar um campo (Professor, Turma ou Matéria) preencha
automaticamente os demais conforme as ForeignKeys cadastradas.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from ..models import Professor, Turma, Materia, Livro, Horario


def _opt(qs, label_attr):
    return [{"id": obj.id, "text": getattr(obj, label_attr)} for obj in qs]


@login_required
@require_GET
def cascade_professor(request, pk):
    """Dado um professor, devolve escola, matéria(s) e turmas vinculadas."""
    try:
        prof = Professor.objects.select_related("escola", "materia").get(pk=pk)
    except Professor.DoesNotExist:
        return JsonResponse({"ok": False}, status=404)

    materias = Materia.objects.filter(professores__id=prof.id).distinct()
    turmas = Turma.objects.filter(horarios__professor_id=prof.id).distinct()
    livros = Livro.objects.filter(escola_id=prof.escola_id, materia_id=prof.materia_id)

    return JsonResponse({
        "ok": True,
        "escola": {"id": prof.escola_id, "text": prof.escola.nome_escola or ""},
        "materia_default": prof.materia_id,
        "materias": _opt(materias, "nome_materia"),
        "turmas": _opt(turmas, "nome_turma"),
        "livros": _opt(livros, "nome_livro"),
    })


@login_required
@require_GET
def cascade_turma(request, pk):
    """Dada uma turma, devolve escola e os professores/matérias vinculadas pelos horários."""
    try:
        turma = Turma.objects.select_related("escola").get(pk=pk)
    except Turma.DoesNotExist:
        return JsonResponse({"ok": False}, status=404)

    professores = Professor.objects.filter(horarios__turma_id=turma.id).distinct()
    materias = Materia.objects.filter(horarios__turma_id=turma.id).distinct()

    return JsonResponse({
        "ok": True,
        "escola": {
            "id": turma.escola_id,
            "text": turma.escola.nome_escola if turma.escola else "",
        },
        "professores": _opt(professores, "nome_professor"),
        "materias": _opt(materias, "nome_materia"),
    })


@login_required
@require_GET
def cascade_materia(request, pk):
    """Dada uma matéria (e opcionalmente escola), devolve professores e livros."""
    escola_id = request.GET.get("escola") or None
    professores = Professor.objects.filter(materia_id=pk)
    livros = Livro.objects.filter(materia_id=pk)
    if escola_id:
        professores = professores.filter(escola_id=escola_id)
        livros = livros.filter(escola_id=escola_id)
    return JsonResponse({
        "ok": True,
        "professores": _opt(professores.distinct(), "nome_professor"),
        "livros": _opt(livros.distinct(), "nome_livro"),
    })
