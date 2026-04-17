from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Materia
from ..forms import MateriaForm


@login_required
def materia_list(request):
    materias = Materia.objects.all()
    return render(request, "diario/materia/list.html", {"materias": materias})


@login_required
def materia_create(request):
    form = MateriaForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Matéria cadastrada com sucesso.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/form.html", {"form": form, "titulo": "Nova Matéria"})


@login_required
def materia_update(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    form = MateriaForm(request.POST or None, instance=materia)
    if form.is_valid():
        form.save()
        messages.success(request, "Matéria atualizada.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/form.html", {"form": form, "titulo": "Editar Matéria"})


@login_required
def materia_delete(request, pk):
    materia = get_object_or_404(Materia, pk=pk)
    if request.method == "POST":
        materia.delete()
        messages.success(request, "Matéria excluída.")
        return redirect("cal:materia_list")
    return render(request, "diario/materia/confirm_delete.html", {"obj": materia, "titulo": "Excluir Matéria"})
