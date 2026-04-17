from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Professor
from ..forms import ProfessorForm


@login_required
def professor_list(request):
    professores = Professor.objects.select_related("escola", "materia").all()
    return render(request, "diario/professor/list.html", {"professores": professores})


@login_required
def professor_create(request):
    form = ProfessorForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Professor(a) cadastrado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Novo Professor"})


@login_required
def professor_update(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    form = ProfessorForm(request.POST or None, instance=professor)
    if form.is_valid():
        form.save()
        messages.success(request, "Professor(a) atualizado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Editar Professor"})


@login_required
def professor_delete(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    if request.method == "POST":
        professor.delete()
        messages.success(request, "Professor(a) excluído(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/confirm_delete.html", {"obj": professor, "titulo": "Excluir Professor"})
