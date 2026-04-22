from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import Professor
from ..forms import ProfessorForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
    escolas_administradas,
)


@admin_escola_required
def professor_list(request):
    professores = filtrar_por_escola(
        Professor.objects.select_related("escola", "materia").all(),
        request.user,
    ).order_by("escola__nome_escola", "nome_professor")
    return render(request, "diario/professor/list.html", {"professores": professores})


def _form_com_escopo(request, instance=None):
    form = ProfessorForm(request.POST or None, instance=instance)
    form.fields["escola"].queryset = escolas_administradas(request.user)
    return form


@admin_escola_required
def professor_create(request):
    form = _form_com_escopo(request)
    if request.method == "POST" and form.is_valid():
        prof = form.save(commit=False)
        if not pode_administrar_escola(request.user, prof.escola):
            return HttpResponseForbidden("Sem permissão para esta escola.")
        prof.save()
        messages.success(request, "Professor(a) cadastrado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Novo Professor"})


@admin_escola_required
def professor_update(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    if not pode_administrar_escola(request.user, professor.escola):
        return HttpResponseForbidden("Sem permissão para editar este professor.")
    form = _form_com_escopo(request, instance=professor)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        messages.success(request, "Professor(a) atualizado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Editar Professor"})


@admin_escola_required
def professor_delete(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    if not pode_administrar_escola(request.user, professor.escola):
        return HttpResponseForbidden("Sem permissão para excluir este professor.")
    if request.method == "POST":
        professor.delete()
        messages.success(request, "Professor(a) excluído(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/confirm_delete.html", {"obj": professor, "titulo": "Excluir Professor"})
