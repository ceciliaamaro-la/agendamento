from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import Turma
from ..forms import TurmaForm
from django.contrib.auth.decorators import login_required
from ..services.escopo import (
    admin_escola_required, admin_estrito_required, _negar,
    pode_administrar_escola, turmas_do_usuario, is_admin_escola, is_coordenador,
    escolas_administradas,
)


@login_required
@admin_escola_required
def turma_list(request):
    turmas = turmas_do_usuario(request.user).select_related('escola').order_by(
        "escola__nome_escola", "nome_turma"
    )
    return render(request, 'turma/list.html', {
        'turmas': turmas,
        'pode_admin': is_admin_escola(request.user) and not is_coordenador(request.user),
    })


def _form_com_escopo(request, instance=None):
    form = TurmaForm(request.POST or None, instance=instance)
    form.fields['escola'].queryset = escolas_administradas(request.user)
    qs = form.fields['escola'].queryset
    if qs.count() == 1:
        unica = qs.first()
        form.fields['escola'].initial = unica.id
        form.fields['escola'].disabled = True
        form.fields['escola'].help_text = "Sua escola foi selecionada automaticamente."
        if not form.is_bound and not form.initial.get('escola'):
            form.initial['escola'] = unica.id
    return form


@admin_estrito_required
def turma_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        turma = form.save(commit=False)
        if not pode_administrar_escola(request.user, turma.escola):
            return _negar(request, "Sem permissão para criar turma nesta escola.")
        turma.save()
        messages.success(request, 'Turma criada com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/form.html', {'form': form, 'titulo': 'Nova Turma'})


@admin_estrito_required
def turma_update(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if not pode_administrar_escola(request.user, turma.escola):
        return _negar(request, "Sem permissão para editar esta turma.")
    form = _form_com_escopo(request, instance=turma)
    if request.method == 'POST' and form.is_valid():
        nova = form.save(commit=False)
        if not pode_administrar_escola(request.user, nova.escola):
            return _negar(request, "Escola fora do seu escopo.")
        nova.save()
        messages.success(request, 'Turma atualizada com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/form.html', {'form': form, 'titulo': 'Editar Turma'})


@admin_estrito_required
def turma_delete(request, pk):
    turma = get_object_or_404(Turma, pk=pk)
    if not pode_administrar_escola(request.user, turma.escola):
        return _negar(request, "Sem permissão para excluir esta turma.")
    if request.method == 'POST':
        turma.delete()
        messages.success(request, 'Turma excluída com sucesso!')
        return redirect('cal:turma_list')
    return render(request, 'turma/confirm_delete.html', {'turma': turma})
