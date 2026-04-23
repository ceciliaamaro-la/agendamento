from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import Livro
from ..forms import LivroForm
from django.contrib.auth.decorators import login_required
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
    escolas_administradas, escolas_do_usuario, is_admin_escola,
)


@login_required
def livro_list(request):
    base = Livro.objects.select_related("escola", "materia").all()
    if is_admin_escola(request.user):
        livros = filtrar_por_escola(base, request.user)
    else:
        livros = base.filter(escola__in=escolas_do_usuario(request.user))
    livros = livros.order_by("escola__nome_escola", "nome_livro")
    return render(request, "diario/livro/list.html", {
        "livros": livros,
        "pode_admin": is_admin_escola(request.user),
    })


def _form_com_escopo(request, instance=None):
    form = LivroForm(request.POST or None, instance=instance)
    form.fields["escola"].queryset = escolas_administradas(request.user)
    return form


@admin_escola_required
def livro_create(request):
    form = _form_com_escopo(request)
    if request.method == "POST" and form.is_valid():
        livro = form.save(commit=False)
        if not pode_administrar_escola(request.user, livro.escola):
            return HttpResponseForbidden("Sem permissão para esta escola.")
        livro.save()
        messages.success(request, "Livro cadastrado.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/form.html", {"form": form, "titulo": "Novo Livro"})


@admin_escola_required
def livro_update(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    if not pode_administrar_escola(request.user, livro.escola):
        return HttpResponseForbidden("Sem permissão para editar este livro.")
    form = _form_com_escopo(request, instance=livro)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        messages.success(request, "Livro atualizado.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/form.html", {"form": form, "titulo": "Editar Livro"})


@admin_escola_required
def livro_delete(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    if not pode_administrar_escola(request.user, livro.escola):
        return HttpResponseForbidden("Sem permissão para excluir este livro.")
    if request.method == "POST":
        livro.delete()
        messages.success(request, "Livro excluído.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/confirm_delete.html", {"obj": livro, "titulo": "Excluir Livro"})
