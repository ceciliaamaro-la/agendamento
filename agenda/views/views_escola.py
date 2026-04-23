from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseForbidden

from agenda.models import Escola
from agenda.forms import EscolaForm
from django.contrib.auth.decorators import login_required
from agenda.services.escopo import (
    admin_escola_required, superadmin_required,
    escolas_administradas, pode_administrar_escola, is_superadmin,
    is_admin_escola, escolas_do_usuario, bloquear_alunos_responsaveis,
)


@bloquear_alunos_responsaveis
def escola_list(request):
    escolas = escolas_do_usuario(request.user).order_by("nome_escola")
    return render(request, 'escola/list.html', {
        'escolas': escolas,
        'pode_criar': is_superadmin(request.user),
        'pode_admin': is_admin_escola(request.user),
    })


@superadmin_required
def escola_nova(request):
    if request.method == 'POST':
        form = EscolaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escola criada com sucesso!')
            return redirect('cal:escola_list')
    else:
        form = EscolaForm()
    return render(request, 'escola/form.html', {'form': form, 'titulo': 'Nova Escola'})


@admin_escola_required
def escola_update(request, pk):
    escola = get_object_or_404(Escola, pk=pk)
    if not pode_administrar_escola(request.user, escola):
        return HttpResponseForbidden("Sem permissão para editar esta escola.")
    if request.method == 'POST':
        form = EscolaForm(request.POST, instance=escola)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escola atualizada com sucesso!')
            return redirect('cal:escola_list')
    else:
        form = EscolaForm(instance=escola)
    return render(request, 'escola/form.html', {'form': form, 'titulo': 'Editar Escola'})


@superadmin_required
def escola_delete(request, pk):
    escola = get_object_or_404(Escola, pk=pk)
    if request.method == 'POST':
        escola.delete()
        messages.success(request, 'Escola excluída com sucesso!')
        return redirect('cal:escola_list')
    return render(request, 'escola/confirm_delete.html', {'escola': escola})
