from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden

from ..models import ProfessorUsuario, Professor
from ..forms import ProfessorUsuarioForm
from ..services.escopo import (
    admin_escola_required, filtrar_por_escola, pode_administrar_escola,
)


@admin_escola_required
def vinculo_list(request):
    qs = ProfessorUsuario.objects.select_related("professor", "professor__escola", "usuario").all()
    professores_visiveis = filtrar_por_escola(Professor.objects.all(), request.user)
    qs = qs.filter(professor__in=professores_visiveis).order_by("professor__nome_professor", "-ativo", "-data_inicio")
    return render(request, "diario/professor_usuario/list.html", {"vinculos": qs})


@admin_escola_required
def vinculo_create(request):
    form = ProfessorUsuarioForm(request.POST or None, initial={"data_inicio": date.today()})
    professores_visiveis = filtrar_por_escola(Professor.objects.all(), request.user)
    form.fields["professor"].queryset = professores_visiveis

    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not pode_administrar_escola(request.user, obj.professor.escola):
            return HttpResponseForbidden("Sem permissão para este professor.")
        # Se for ativo: encerra qualquer vínculo ativo anterior do mesmo professor
        if obj.ativo:
            ProfessorUsuario.objects.filter(
                professor=obj.professor, ativo=True
            ).exclude(pk=obj.pk or 0).update(ativo=False, data_fim=date.today())
        obj.save()
        messages.success(request, "Vínculo criado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/form.html", {"form": form, "titulo": "Novo Vínculo"})


@admin_escola_required
def vinculo_update(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return HttpResponseForbidden("Sem permissão.")
    form = ProfessorUsuarioForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.professor.escola):
            return HttpResponseForbidden("Sem permissão.")
        if novo.ativo:
            ProfessorUsuario.objects.filter(
                professor=novo.professor, ativo=True
            ).exclude(pk=novo.pk).update(ativo=False, data_fim=date.today())
        novo.save()
        messages.success(request, "Vínculo atualizado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/form.html", {"form": form, "titulo": "Editar Vínculo"})


@admin_escola_required
def vinculo_encerrar(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return HttpResponseForbidden("Sem permissão.")
    if request.method == "POST":
        obj.encerrar()
        messages.success(request, "Vínculo encerrado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/confirm_encerrar.html", {"obj": obj, "titulo": "Encerrar Vínculo"})


@admin_escola_required
def vinculo_delete(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return HttpResponseForbidden("Sem permissão.")
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Vínculo excluído.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/confirm_delete.html", {"obj": obj, "titulo": "Excluir Vínculo"})
