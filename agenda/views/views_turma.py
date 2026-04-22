from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import Turma
from ..forms import TurmaForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
)


@admin_escola_required
def turma_list(request):
    turmas = filtrar_por_escola(
        Turma.objects.select_related('escola').all(),
        request.user,
    ).order_by("escola__nome_escola", "nome_turma")
    return render(request, 'turma/list.html', {'turmas': turmas})


def _form_com_escopo(request, instance=None):
    form = TurmaForm(request.POST or None, instance=instance)
    from ..services.escopo import escolas_administradas
    form.fields['escola'].queryset = escolas_administradas(request.user)
    return form


@admin_escola_required
def turma_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        turma = form.save(commit=False)
        if not pode_administrar_escola(request.user, turma.escola):
            return HttpResponseForbidden("Sem permissão para criar turma nesta escola.")
        turma.save()
        messages.success(request, 'Turma criada com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/form.html', {'form': form, 'titulo': 'Nova Turma'})


@admin_escola_required
def turma_update(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if not pode_administrar_escola(request.user, turma.escola):
        return HttpResponseForbidden("Sem permissão para editar esta turma.")
    form = _form_com_escopo(request, instance=turma)
    if request.method == 'POST' and form.is_valid():
        nova = form.save(commit=False)
        if not pode_administrar_escola(request.user, nova.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        nova.save()
        messages.success(request, 'Turma atualizada com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/form.html', {'form': form, 'titulo': 'Editar Turma'})


@admin_escola_required
def turma_delete(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if not pode_administrar_escola(request.user, turma.escola):
        return HttpResponseForbidden("Sem permissão para excluir esta turma.")
    if request.method == 'POST':
        turma.delete()
        messages.success(request, 'Turma excluída com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/confirm_delete.html', {'turma': turma})
