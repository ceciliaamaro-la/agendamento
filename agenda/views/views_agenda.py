from django.shortcuts import render, redirect, get_object_or_404
from django.utils.formats import get_format
from ..models import AgendaEvento
from ..forms import AgendaEventoForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def agenda_list(request):
    # Order by inicio when available, fall back to legacy data field.
    agendas = AgendaEvento.objects.select_related('turma').order_by(
        '-inicio', '-data'
    )
    return render(request, 'agenda/list.html', {'agendas': agendas})

@login_required
def agenda_create(request):
    if request.method == 'POST':
        form = AgendaEventoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evento criado com sucesso!')
            return redirect('cal:agenda_list')
    else:
        form = AgendaEventoForm()
    return render(request, 'agenda/form.html', {'form': form, 'titulo': 'Novo Evento'})

@login_required
def agenda_update(request, pk):
    agenda = get_object_or_404(AgendaEvento, pk=pk)
    if request.method == 'POST':
        form = AgendaEventoForm(request.POST, instance=agenda)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evento atualizado com sucesso!')
            return redirect('cal:agenda_list')
    else:
        form = AgendaEventoForm(instance=agenda)
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
