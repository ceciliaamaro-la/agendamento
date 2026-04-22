from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import WhatsAppEnvio
from ..forms import WhatsAppEnvioForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
    turmas_do_usuario, escolas_administradas,
)


@admin_escola_required
def whats_list(request):
    envios = filtrar_por_escola(
        WhatsAppEnvio.objects.select_related('turma', 'turma__escola'),
        request.user,
        escola_lookup='turma__escola',
    ).order_by('-enviado_em')
    return render(request, 'whats/list.html', {'whatss': envios})


def _form_com_escopo(request, instance=None):
    form = WhatsAppEnvioForm(request.POST or None, instance=instance)
    form.fields['turma'].queryset = turmas_do_usuario(request.user).filter(
        escola__in=escolas_administradas(request.user)
    )
    return form


@admin_escola_required
def whats_create(request):
    form = _form_com_escopo(request)
    if request.method == 'POST' and form.is_valid():
        env = form.save(commit=False)
        if not pode_administrar_escola(request.user, env.turma.escola):
            return HttpResponseForbidden("Sem permissão para esta escola.")
        env.save()
        messages.success(request, 'Registro de envio criado com sucesso!')
        return redirect('cal:whats_list')
    return render(request, 'whats/form.html', {'form': form, 'titulo': 'Novo Envio WhatsApp'})


@admin_escola_required
def whats_update(request, pk):
    env = get_object_or_404(WhatsAppEnvio, pk=pk)
    if not pode_administrar_escola(request.user, env.turma.escola):
        return HttpResponseForbidden("Sem permissão para editar.")
    form = _form_com_escopo(request, instance=env)
    if request.method == 'POST' and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.turma.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        messages.success(request, 'Registro atualizado com sucesso!')
        return redirect('cal:whats_list')
    return render(request, 'whats/form.html', {'form': form, 'titulo': 'Editar Envio WhatsApp'})


@admin_escola_required
def whats_delete(request, pk):
    env = get_object_or_404(WhatsAppEnvio, pk=pk)
    if not pode_administrar_escola(request.user, env.turma.escola):
        return HttpResponseForbidden("Sem permissão para excluir.")
    if request.method == 'POST':
        env.delete()
        messages.success(request, 'Registro excluído com sucesso!')
        return redirect('cal:whats_list')
    return render(request, 'whats/confirm_delete.html', {'whats': env})
