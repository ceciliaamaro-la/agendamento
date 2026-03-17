import json
import logging
from datetime import date, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from ..models import Aluno, AgendaEvento, TarefaCompleta

logger = logging.getLogger(__name__)


@login_required
def listar_tarefas(request):
    """
    Detecta automaticamente os alunos vinculados ao usuário logado.
    Se tiver mais de um aluno, permite selecionar via ?aluno_id=.
    Filtra eventos: 1 dia anterior + hoje + 7 dias à frente.
    Separa em pendentes e concluídas.
    """
    alunos_do_usuario = Aluno.objects.filter(
        usuarios=request.user
    ).select_related('turma').order_by('nome_aluno')

    if not alunos_do_usuario.exists():
        return render(request, 'tarefas/sem_aluno.html', {})

    # Seleciona o aluno: primeiro da lista ou o que o usuário escolheu
    aluno_id = request.GET.get('aluno_id')
    if aluno_id:
        aluno = get_object_or_404(alunos_do_usuario, pk=aluno_id)
    else:
        aluno = alunos_do_usuario.first()

    # Janela de datas: ontem até daqui 7 dias
    hoje = date.today()
    data_inicio = hoje - timedelta(days=1)
    data_fim = hoje + timedelta(days=7)

    eventos = (
        AgendaEvento.objects
        .filter(turma=aluno.turma, data__gte=data_inicio, data__lte=data_fim)
        .order_by("data")
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
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    })


@require_POST
@login_required
def marcar_concluida(request):
    """
    Endpoint AJAX para marcar/desmarcar uma tarefa como concluída.
    Payload JSON: { "evento_id": int, "aluno_id": int }
    Resposta JSON: { "status": "ok", "concluida": bool }
    """
    try:
        data = json.loads(request.body)
        evento_id = int(data.get("evento_id"))
        aluno_id = int(data.get("aluno_id"))
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Payload inválido em marcar_concluida: {e}")
        return JsonResponse({"status": "erro", "mensagem": "Dados inválidos."}, status=400)

    # Verifica que o aluno pertence ao usuário logado
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
