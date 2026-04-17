from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import OrdemHorario
from ..forms import OrdemHorarioForm


@login_required
def ordem_list(request):
    ordens = OrdemHorario.objects.all()
    return render(request, "diario/ordem_horario/list.html", {"ordens": ordens})


@login_required
def ordem_create(request):
    form = OrdemHorarioForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Período cadastrado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Novo Período"})


@login_required
def ordem_update(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    form = OrdemHorarioForm(request.POST or None, instance=ordem)
    if form.is_valid():
        form.save()
        messages.success(request, "Período atualizado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Editar Período"})


@login_required
def ordem_delete(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if request.method == "POST":
        ordem.delete()
        messages.success(request, "Período excluído.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/confirm_delete.html", {"obj": ordem, "titulo": "Excluir Período"})
