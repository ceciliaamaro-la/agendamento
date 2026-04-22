"""Matérias e Períodos são GLOBAIS (compartilhados entre escolas).

- Listagem: visível para qualquer admin_escola (precisa para cadastrar professores/horários)
- Criação/edição/exclusão: somente super-administrador
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import Materia
from ..forms import MateriaForm
from ..services.escopo import admin_escola_required, superadmin_required


@admin_escola_required
def materia_list(request):
    materias = Materia.objects.all().order_by("nome_materia")
    return render(request, "diario/materia/list.html", {"materias": materias})


@superadmin_required
def materia_create(request):
    form = MateriaForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Matéria cadastrada com sucesso.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/form.html", {"form": form, "titulo": "Nova Matéria"})


@superadmin_required
def materia_update(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    form = MateriaForm(request.POST or None, instance=materia)
    if form.is_valid():
        form.save()
        messages.success(request, "Matéria atualizada.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/form.html", {"form": form, "titulo": "Editar Matéria"})


@superadmin_required
def materia_delete(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    if request.method == "POST":
        materia.delete()
        messages.success(request, "Matéria excluída.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/confirm_delete.html", {"obj": materia, "titulo": "Excluir Matéria"})
