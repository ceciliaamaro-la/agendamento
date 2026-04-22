from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import Aluno
from ..forms import AlunoForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
    turmas_do_usuario, escolas_administradas,
)


@admin_escola_required
def aluno_list(request):
    alunos = filtrar_por_escola(
        Aluno.objects.select_related('turma', 'turma__escola').prefetch_related('usuarios'),
        request.user,
        escola_lookup='turma__escola',
    ).order_by('turma__escola__nome_escola', 'turma__nome_turma', 'nome_aluno')
    return render(request, 'aluno/list.html', {'alunos': alunos})


def _form_com_escopo(request, instance=None):
    form = AlunoForm(request.POST or None, instance=instance)
    form.fields['turma'].queryset = turmas_do_usuario(request.user).filter(
        escola__in=escolas_administradas(request.user)
    )
    return form


@admin_escola_required
def aluno_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        aluno = form.save(commit=False)
        if not pode_administrar_escola(request.user, aluno.turma.escola):
            return HttpResponseForbidden("Sem permissão para criar aluno nessa escola.")
        aluno.save()
        form.save_m2m()
        messages.success(request, 'Aluno criado com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Novo Aluno'})


@admin_escola_required
def aluno_update(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if not pode_administrar_escola(request.user, aluno.turma.escola):
        return HttpResponseForbidden("Sem permissão para editar este aluno.")
    form = _form_com_escopo(request, instance=aluno)
    if request.method == 'POST' and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.turma.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        form.save_m2m()
        messages.success(request, 'Aluno atualizado com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Editar Aluno'})


@admin_escola_required
def aluno_delete(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if not pode_administrar_escola(request.user, aluno.turma.escola):
        return HttpResponseForbidden("Sem permissão para excluir este aluno.")
    if request.method == 'POST':
        aluno.delete()
        messages.success(request, 'Aluno excluído com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/confirm_delete.html', {'aluno': aluno})
