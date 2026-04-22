import hashlib
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.formats import get_format
from ..models import AgendaEvento
from ..forms import AgendaEventoForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def _gerar_hash_manual(evento) -> str:
    base = f"manual-{evento.pk or secrets.token_hex(8)}-{evento.titulo}-{evento.inicio}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

@login_required
def agenda_list(request):
    # Order by inicio when available, fall back to legacy data field.
    agendas = AgendaEvento.objects.select_related(
        'turma', 'turma__escola', 'escola', 'professor', 'materia'
    ).order_by('-inicio', '-data')
    return render(request, 'agenda/list.html', {'agendas': agendas})

@login_required
def agenda_create(request):
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
    agenda = get_object_or_404(AgendaEvento, pk=pk)
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
    agenda = get_object_or_404(AgendaEvento, pk=pk)
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
            deleted, _ = AgendaEvento.objects.filter(pk__in=ids).delete()
            messages.success(request, f'{deleted} evento(s) excluído(s).')
        else:
            messages.warning(request, 'Nenhum evento selecionado.')
    return redirect('cal:agenda_list')
