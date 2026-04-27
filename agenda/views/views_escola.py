from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from agenda.models import Escola, LogAuditoria
from agenda.forms import EscolaForm
from agenda.services.escopo import (
    admin_escola_required, admin_estrito_required, superadmin_required, _negar,
    escolas_administradas, pode_administrar_escola, is_superadmin,
    is_admin_escola, escolas_do_usuario, is_coordenador,
)
from agenda.services.auditoria import registrar as registrar_auditoria


@admin_escola_required
def escola_list(request):
    escolas = escolas_do_usuario(request.user).order_by("nome_escola")
    return render(request, 'escola/list.html', {
        'escolas': escolas,
        'pode_criar': is_superadmin(request.user),
        'pode_admin': is_admin_escola(request.user) and not is_coordenador(request.user),
    })


@superadmin_required
def escola_nova(request):
    if request.method == 'POST':
        form = EscolaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escola criada com sucesso!')
            return redirect('cal:escola_list')
    else:
        form = EscolaForm()
    return render(request, 'escola/form.html', {'form': form, 'titulo': 'Nova Escola'})


@admin_estrito_required
def escola_update(request, pk):
    escola = get_object_or_404(Escola, pk=pk)
    if not pode_administrar_escola(request.user, escola):
        return _negar(request, "Sem permissão para editar esta escola.")
    if request.method == 'POST':
        form = EscolaForm(request.POST, request.FILES, instance=escola)
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
        nome_escola = escola.nome_escola
        escola_id = escola.pk
        escola.delete()
        registrar_auditoria(
            request.user,
            LogAuditoria.ACAO_EXCLUIR_ESCOLA,
            f"Excluiu a escola '{nome_escola}'.",
            recurso="Escola",
            recurso_id=escola_id,
            detalhes={"nome_escola": nome_escola},
        )
        messages.success(request, 'Escola excluída com sucesso!')
        return redirect('cal:escola_list')
    return render(request, 'escola/confirm_delete.html', {'escola': escola})
