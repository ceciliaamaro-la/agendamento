import hashlib
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.utils.formats import get_format
from ..models import AgendaEvento
from ..forms import AgendaEventoForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..services.escopo import (
    eventos_do_usuario, pode_editar_evento, is_admin_escola, is_professor,
    professor_do_usuario,
)


def _gerar_hash_manual(evento) -> str:
    base = f"manual-{evento.pk or secrets.token_hex(8)}-{evento.titulo}-{evento.inicio}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _evento_ou_403(request, pk):
    ev = get_object_or_404(AgendaEvento, pk=pk)
    if not pode_editar_evento(request.user, ev):
        return None, HttpResponseForbidden("Sem permissão para editar este evento.")
    return ev, None


@login_required
def agenda_list(request):
    agendas = eventos_do_usuario(request.user).select_related(
        'turma', 'turma__escola', 'escola', 'professor', 'materia'
    ).order_by('-inicio', '-data')
    return render(request, 'agenda/list.html', {
        'agendas': agendas,
        'pode_criar': is_admin_escola(request.user) or is_professor(request.user),
    })


@login_required
def agenda_create(request):
    from ..services.escopo import is_aluno, is_responsavel
    if is_aluno(request.user) or is_responsavel(request.user):
        return HttpResponseForbidden("Sem permissão para criar eventos.")
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
