import hashlib
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.formats import get_format
from ..models import AgendaEvento
from ..forms import AgendaEventoForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..services.escopo import (
    eventos_do_usuario, pode_editar_evento, is_admin_escola, is_professor,
    professor_do_usuario, _negar,
)


def _gerar_hash_manual(evento) -> str:
    base = f"manual-{evento.pk or secrets.token_hex(8)}-{evento.titulo}-{evento.inicio}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _evento_ou_403(request, pk):
    ev = get_object_or_404(AgendaEvento, pk=pk)
    if not pode_editar_evento(request.user, ev):
        return None, _negar(request, "Sem permissão para editar este evento.")
    return ev, None


@login_required
def agenda_list(request):
    from collections import OrderedDict
    from ..services.agrupamento import estruturar
    from ..services.escopo import turmas_do_usuario

    turma_id = request.GET.get("turma")
    agendas = eventos_do_usuario(request.user).select_related(
        'turma', 'turma__escola', 'escola', 'professor', 'materia'
    )
    if turma_id:
        agendas = agendas.filter(turma_id=turma_id)
    agendas = agendas.order_by(
        'turma__escola__nome_escola', 'turma__nome_turma',
        'materia__nome_materia', '-inicio', '-data'
    )

    triples = []
    eventos_escola_dict = OrderedDict()
    for ev in agendas:
        if ev.turma_id is None:
            esc_nome = ev.escola.nome_escola if ev.escola else "—"
            eventos_escola_dict.setdefault(esc_nome, []).append(ev)
            continue
        esc_nome = ev.turma.escola.nome_escola if ev.turma.escola else "—"
        triples.append((esc_nome, ev.turma, ev.materia, ev))

    escolas = estruturar(
        triples,
        sem_materia_label="Eventos da Turma",
        sem_materia_icon="people-fill",
    )
    eventos_escola = [
        {"nome": k, "items": v} for k, v in eventos_escola_dict.items()
    ]

    turmas = turmas_do_usuario(request.user).select_related("escola").order_by(
        "escola__nome_escola", "nome_turma"
    )
    return render(request, 'agenda/list.html', {
        'escolas': escolas,
        'eventos_escola': eventos_escola,
        'tem_eventos': bool(escolas) or bool(eventos_escola),
        'turmas': turmas,
        'turma_filtro': turma_id,
        'pode_criar': is_admin_escola(request.user) or is_professor(request.user),
    })


@login_required
def agenda_create(request):
    from ..services.escopo import is_aluno, is_responsavel
    if is_aluno(request.user) or is_responsavel(request.user):
        return _negar(request, "Alunos e responsáveis não podem criar eventos.")
    if request.method == 'POST':
        form = AgendaEventoForm(request.POST, user=request.user)
        if form.is_valid():
            evento = form.save(commit=False)
            if not evento.hash:
                evento.hash = _gerar_hash_manual(evento)
            evento.save()
            if evento.turma_id:
                request.session["ultima_turma_id"] = evento.turma_id
            messages.success(request, 'Evento criado com sucesso!')
            return redirect('cal:agenda_list')
    else:
        initial = {}
        ultima_turma = request.session.get("ultima_turma_id")
        if ultima_turma:
            initial["turma"] = ultima_turma
        form = AgendaEventoForm(user=request.user, initial=initial)
    return render(request, 'agenda/form.html', {'form': form, 'titulo': 'Novo Evento'})

@login_required
def agenda_update(request, pk):
    agenda, forbidden = _evento_ou_403(request, pk)
    if forbidden:
        return forbidden
    if request.method == 'POST':
        form = AgendaEventoForm(request.POST, instance=agenda, user=request.user)
        if form.is_valid():
            evento = form.save(commit=False)
            if not evento.hash:
                evento.hash = _gerar_hash_manual(evento)
            evento.save()
            messages.success(request, 'Evento atualizado com sucesso!')
            return redirect('cal:agenda_list')
    else:
        form = AgendaEventoForm(instance=agenda, user=request.user)
    return render(request, 'agenda/form.html', {'form': form, 'titulo': 'Editar Evento'})

@login_required
def agenda_delete(request, pk):
    agenda, forbidden = _evento_ou_403(request, pk)
    if forbidden:
        return forbidden
    if request.method == 'POST':
        agenda.delete()
        messages.success(request, 'Evento excluído com sucesso!')
        return redirect('cal:agenda_list')
    return render(request, 'agenda/confirm_delete.html', {'agenda': agenda})


@login_required
def agenda_delete_bulk(request):
    if request.method == 'POST':
        ids = request.POST.getlist('ids')
        if ids:
            permitidos = [
                ev.pk for ev in AgendaEvento.objects.filter(pk__in=ids)
                if pode_editar_evento(request.user, ev)
            ]
            if permitidos:
                deleted, _ = AgendaEvento.objects.filter(pk__in=permitidos).delete()
                messages.success(request, f'{deleted} evento(s) excluído(s).')
            recusados = len(ids) - len(permitidos)
            if recusados:
                messages.warning(request, f'{recusados} evento(s) não puderam ser excluídos (sem permissão).')
        else:
            messages.warning(request, 'Nenhum evento selecionado.')
    return redirect('cal:agenda_list')
