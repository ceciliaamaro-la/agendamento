from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import Aluno
from ..forms import AlunoForm
from django.contrib.auth.decorators import login_required
from ..services.escopo import (
    admin_escola_required, admin_estrito_required, _negar,
    filtrar_por_escola, pode_administrar_escola,
    turmas_do_usuario, escolas_administradas, is_admin_escola, is_professor,
    is_aluno, is_responsavel, turmas_do_professor, is_coordenador,
)


@login_required
def aluno_list(request):
    if is_aluno(request.user):
        return _negar(request, "Alunos não acessam a lista geral. Acesse 'Minhas Tarefas'.")
    base = Aluno.objects.select_related('turma', 'turma__escola').prefetch_related('usuarios')
    if is_admin_escola(request.user):
        alunos = filtrar_por_escola(base, request.user, escola_lookup='turma__escola')
    elif is_professor(request.user):
        alunos = base.filter(turma__in=turmas_do_professor(request.user))
    elif is_responsavel(request.user):
        alunos = base.filter(usuarios=request.user)
    else:
        alunos = base.none()
    alunos = alunos.order_by('turma__escola__nome_escola', 'turma__nome_turma', 'nome_aluno')
    return render(request, 'aluno/list.html', {
        'alunos': alunos,
        'pode_admin': is_admin_escola(request.user) and not is_coordenador(request.user),
    })


def _form_com_escopo(request, instance=None):
    form = AlunoForm(request.POST or None, instance=instance)
    form.fields['turma'].queryset = turmas_do_usuario(request.user).filter(
        escola__in=escolas_administradas(request.user)
    )
    return form


@admin_estrito_required
def aluno_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        aluno = form.save(commit=False)
        if not pode_administrar_escola(request.user, aluno.turma.escola):
            return _negar(request, "Sem permissão para criar aluno nessa escola.")
        aluno.save()
        form.save_m2m()
        messages.success(request, 'Aluno criado com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Novo Aluno'})


@admin_estrito_required
def aluno_update(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if not pode_administrar_escola(request.user, aluno.turma.escola):
        return _negar(request, "Sem permissão para editar este aluno.")
    form = _form_com_escopo(request, instance=aluno)
    if request.method == 'POST' and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.turma.escola):
            return _negar(request, "Escola fora do seu escopo.")
        novo.save()
        form.save_m2m()
        messages.success(request, 'Aluno atualizado com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Editar Aluno'})


@admin_estrito_required
def aluno_delete(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if not pode_administrar_escola(request.user, aluno.turma.escola):
        return _negar(request, "Sem permissão para excluir este aluno.")
    if request.method == 'POST':
        aluno.delete()
        messages.success(request, 'Aluno excluído com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/confirm_delete.html', {'aluno': aluno})
