from django.shortcuts import render, redirect, get_object_or_404
from ..models import Aluno
from ..forms import AlunoForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def aluno_list(request):
    alunos = Aluno.objects.select_related('turma').prefetch_related('usuarios').all()
    return render(request, 'aluno/list.html', {'alunos': alunos})

@login_required
def aluno_create(request):
    if request.method == 'POST':
        form = AlunoForm(request.POST)
        if form.is_valid():
            aluno = form.save()
            messages.success(request, 'Aluno criado com sucesso!')
            return redirect('cal:aluno_list')
    else:
        form = AlunoForm()
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Novo Aluno'})

@login_required
def aluno_update(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        form = AlunoForm(request.POST, instance=aluno)
        if form.is_valid():
            form.save()
            messages.success(request, 'Aluno atualizado com sucesso!')
            return redirect('cal:aluno_list')
    else:
        form = AlunoForm(instance=aluno)
    return render(request, 'aluno/form.html', {'form': form, 'titulo': 'Editar Aluno'})

@login_required
def aluno_delete(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        aluno.delete()
        messages.success(request, 'Aluno excluído com sucesso!')
        return redirect('cal:aluno_list')
    return render(request, 'aluno/confirm_delete.html', {'aluno': aluno})
