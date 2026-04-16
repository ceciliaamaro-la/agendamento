import json
import logging
from datetime import date, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q

from ..models import Aluno, AgendaEvento, TarefaCompleta

logger = logging.getLogger(__name__)


@login_required
def listar_tarefas(request):
    """
    Shows tasks for the logged-in user's students.

    Window: yesterday through end of next month, covering both legacy
    records (filtered by `data`) and new records (filtered by `inicio`).
    """
    alunos_do_usuario = Aluno.objects.filter(
        usuarios=request.user
    ).select_related('turma').order_by('nome_aluno')

    if not alunos_do_usuario.exists():
        return render(request, 'tarefas/sem_aluno.html', {})

    aluno_id = request.GET.get('aluno_id')
    if aluno_id:
        aluno = get_object_or_404(alunos_do_usuario, pk=aluno_id)
    else:
        aluno = alunos_do_usuario.first()

    # Window: yesterday → end of next month
    hoje = date.today()
    data_inicio = hoje - timedelta(days=1)
    primeiro_proximo = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
    data_fim = (primeiro_proximo + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Include events that match the window via either field.
    # Records from the new robot have inicio set; legacy records use data.
    eventos = (
        AgendaEvento.objects
        .filter(turma=aluno.turma)
        .filter(
            Q(inicio__date__gte=data_inicio, inicio__date__lte=data_fim) |
            Q(inicio__isnull=True, data__gte=data_inicio, data__lte=data_fim)
        )
        .select_related("turma")
        .order_by("inicio", "data")
    )

    concluidos_ids = set(
        TarefaCompleta.objects
        .filter(aluno=aluno, concluida=True)
        .values_list("evento_id", flat=True)
    )

    pendentes = []
    concluidas = []
    for evento in eventos:
        item = {"evento": evento, "concluida": evento.id in concluidos_ids}
        if evento.id in concluidos_ids:
            concluidas.append(item)
        else:
            pendentes.append(item)

    return render(request, "tarefas/lista.html", {
        "aluno": aluno,
        "alunos": alunos_do_usuario,
        "pendentes": pendentes,
        "concluidas": concluidas,
        "hoje": hoje,
        "amanha": hoje + timedelta(days=1),
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    })


@require_POST
@login_required
def marcar_concluida(request):
    """
    AJAX endpoint to toggle a task as done/undone.
    Payload JSON: { "evento_id": int, "aluno_id": int }
    Response JSON: { "status": "ok", "concluida": bool }
    """
    try:
        data = json.loads(request.body)
        evento_id = int(data.get("evento_id"))
        aluno_id = int(data.get("aluno_id"))
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Payload inválido em marcar_concluida: {e}")
        return JsonResponse({"status": "erro", "mensagem": "Dados inválidos."}, status=400)

    aluno = get_object_or_404(Aluno, pk=aluno_id, usuarios=request.user)
    evento = get_object_or_404(AgendaEvento, pk=evento_id)

    tarefa, _ = TarefaCompleta.objects.get_or_create(
        aluno=aluno,
        evento=evento,
        defaults={"concluida": False}
    )

    tarefa.concluida = not tarefa.concluida
    tarefa.save()

    logger.info(
        f"{'✅' if tarefa.concluida else '⬜'} "
        f"Aluno {aluno} — {evento.titulo} — concluida={tarefa.concluida}"
    )

    return JsonResponse({"status": "ok", "concluida": tarefa.concluida})
