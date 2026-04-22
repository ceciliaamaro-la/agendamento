import json
import logging
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from ..models import Aluno, AgendaEvento, TarefaCompleta

logger = logging.getLogger(__name__)

BRASILIA = ZoneInfo("America/Sao_Paulo")


@login_required
def listar_tarefas(request):
    """
    Shows tasks for the logged-in user's students.

    Window: first day of current month → end of next month.
    Filters on the local Brasília date to avoid UTC boundary issues.
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

    # Window: full previous month + full current month + 10 days of next month
    hoje = date.today()
    primeiro_mes_atual = hoje.replace(day=1)
    primeiro_mes_anterior = (primeiro_mes_atual - timedelta(days=1)).replace(day=1)
    ultimo_mes_atual = (primeiro_mes_atual + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    data_inicio = primeiro_mes_anterior          # 1st of previous month
    data_fim = ultimo_mes_atual + timedelta(days=10)  # 10 days into next month

    # inicio is stored as UTC. Convert window boundaries to UTC-aware datetimes
    # so the comparison is done correctly regardless of DST.
    from datetime import datetime
    inicio_utc = datetime(data_inicio.year, data_inicio.month, data_inicio.day,
                          tzinfo=BRASILIA)
    fim_utc = datetime(data_fim.year, data_fim.month, data_fim.day,
                       23, 59, 59, tzinfo=BRASILIA)

    # Include events that match the window via either field.
    # New records have inicio set; legacy records use data.
    eventos = (
        AgendaEvento.objects
        .filter(turma=aluno.turma)
        .filter(
            Q(inicio__gte=inicio_utc, inicio__lte=fim_utc) |
            Q(inicio__isnull=True, data__gte=data_inicio, data__lte=data_fim)
        )
        .select_related("turma", "materia", "professor")
        .order_by("inicio", "data")
    )

    # Only load TarefaCompleta records that are still visible to this student.
    tarefas_do_aluno = {
        t.evento_id: t
        for t in TarefaCompleta.objects.filter(aluno=aluno, visivel=True)
    }

    pendentes = []
    concluidas = []
    for evento in eventos:
        tarefa = tarefas_do_aluno.get(evento.id)
        # Skip events the student explicitly hid (visivel=False records are
        # excluded from tarefas_do_aluno, so they simply won't appear here).
        concluida = tarefa.concluida if tarefa else False
        item = {"evento": evento, "concluida": concluida}
        if concluida:
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


@require_POST
@login_required
def ocultar_tarefa(request):
    """
    AJAX endpoint to hide a completed task from the student's list.

    Sets visivel=False on the student's TarefaCompleta record. The event
    itself and other students' records are not affected.

    Payload JSON: { "evento_id": int, "aluno_id": int }
    Response JSON: { "status": "ok" }
    """
    try:
        data = json.loads(request.body)
        evento_id = int(data.get("evento_id"))
        aluno_id = int(data.get("aluno_id"))
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Payload inválido em ocultar_tarefa: {e}")
        return JsonResponse({"status": "erro", "mensagem": "Dados inválidos."}, status=400)

    aluno = get_object_or_404(Aluno, pk=aluno_id, usuarios=request.user)
    evento = get_object_or_404(AgendaEvento, pk=evento_id)

    tarefa, _ = TarefaCompleta.objects.get_or_create(
        aluno=aluno,
        evento=evento,
        defaults={"concluida": True, "visivel": False},
    )
    tarefa.visivel = False
    tarefa.save()

    logger.info(f"🙈 Aluno {aluno} ocultou — {evento.titulo}")

    return JsonResponse({"status": "ok"})
