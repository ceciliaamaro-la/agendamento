from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Livro
from ..forms import LivroForm


@login_required
def livro_list(request):
    livros = Livro.objects.select_related("escola", "materia").all()
    return render(request, "diario/livro/list.html", {"livros": livros})


@login_required
def livro_create(request):
    form = LivroForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Livro cadastrado.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/form.html", {"form": form, "titulo": "Novo Livro"})


@login_required
def livro_update(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    form = LivroForm(request.POST or None, instance=livro)
    if form.is_valid():
        form.save()
        messages.success(request, "Livro atualizado.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/form.html", {"form": form, "titulo": "Editar Livro"})


@login_required
def livro_delete(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    if request.method == "POST":
        livro.delete()
        messages.success(request, "Livro excluído.")
        return redirect("cal:livro_list")
    return render(request, "diario/livro/confirm_delete.html", {"obj": livro, "titulo": "Excluir Livro"})
