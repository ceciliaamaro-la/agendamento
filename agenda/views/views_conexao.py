from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import ConexaoAgenda
from ..forms import ConexaoAgendaForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
    turmas_do_usuario, escolas_administradas,
)


@admin_escola_required
def conexao_list(request):
    conexoes = filtrar_por_escola(
        ConexaoAgenda.objects.select_related('turma', 'turma__escola'),
        request.user,
        escola_lookup='turma__escola',
    ).order_by('turma__escola__nome_escola', 'turma__nome_turma')
    return render(request, 'conexao/list.html', {'conexaos': conexoes})


def _form_com_escopo(request, instance=None):
    form = ConexaoAgendaForm(request.POST or None, instance=instance)
    form.fields['turma'].queryset = turmas_do_usuario(request.user).filter(
        escola__in=escolas_administradas(request.user)
    )
    return form


@admin_escola_required
def conexao_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        cx = form.save(commit=False)
        if not pode_administrar_escola(request.user, cx.turma.escola):
            return HttpResponseForbidden("Sem permissão para esta escola.")
        cx.save()
        messages.success(request, 'Conexão criada com sucesso!')
        return redirect('cal:conexao_list')
    return render(request, 'conexao/form.html', {'form': form, 'titulo': 'Nova Conexão'})


@admin_escola_required
def conexao_update(request, pk):
    cx = get_object_or_404(ConexaoAgenda, pk=pk)
    if not pode_administrar_escola(request.user, cx.turma.escola):
        return HttpResponseForbidden("Sem permissão para editar esta conexão.")
    form = _form_com_escopo(request, instance=cx)
    if request.method == 'POST' and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.turma.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        messages.success(request, 'Conexão atualizada com sucesso!')
        return redirect('cal:conexao_list')
    return render(request, 'conexao/form.html', {'form': form, 'titulo': 'Editar Conexão'})


@admin_escola_required
def conexao_delete(request, pk):
    cx = get_object_or_404(ConexaoAgenda, pk=pk)
    if not pode_administrar_escola(request.user, cx.turma.escola):
        return HttpResponseForbidden("Sem permissão para excluir esta conexão.")
    if request.method == 'POST':
        cx.delete()
        messages.success(request, 'Conexão excluída com sucesso!')
        return redirect('cal:conexao_list')
    return render(request, 'conexao/confirm_delete.html', {'conexao': cx})
