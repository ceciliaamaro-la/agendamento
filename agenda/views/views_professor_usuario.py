from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import ProfessorUsuario, Professor
from ..forms import ProfessorUsuarioForm
from ..services.escopo import (
    admin_escola_required, admin_estrito_required, _negar,
    filtrar_por_escola, pode_administrar_escola,
    is_admin_escola, professor_do_usuario,
    professor_ou_admin_required, is_coordenador,
)


@professor_ou_admin_required
def vinculo_list(request):
    qs = ProfessorUsuario.objects.select_related("professor", "professor__escola", "usuario").all()
    if is_admin_escola(request.user):
        professores_visiveis = filtrar_por_escola(Professor.objects.all(), request.user)
        qs = qs.filter(professor__in=professores_visiveis)
        pode_admin = not is_coordenador(request.user)
    else:
        # Professor: vê apenas o próprio histórico (read-only)
        prof = professor_do_usuario(request.user)
        qs = qs.filter(professor=prof) if prof else qs.none()
        pode_admin = False
    qs = qs.order_by("professor__nome_professor", "-ativo", "-data_inicio")
    return render(request, "diario/professor_usuario/list.html", {
        "vinculos": qs,
        "pode_admin": pode_admin,
    })


@admin_estrito_required
def vinculo_create(request):
    form = ProfessorUsuarioForm(
        request.POST or None,
        initial={"data_inicio": date.today()},
        request_user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not pode_administrar_escola(request.user, obj.professor.escola):
            return _negar(request, "Sem permissão para este professor.")
        # Se for ativo: encerra qualquer vínculo ativo anterior do mesmo professor
        if obj.ativo:
            ProfessorUsuario.objects.filter(
                professor=obj.professor, ativo=True
            ).exclude(pk=obj.pk or 0).update(ativo=False, data_fim=date.today())
        obj.save()
        messages.success(request, "Vínculo criado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/form.html", {"form": form, "titulo": "Novo Vínculo"})


@admin_estrito_required
def vinculo_update(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return _negar(request, "Sem permissão para editar este vínculo.")
    form = ProfessorUsuarioForm(request.POST or None, instance=obj, request_user=request.user)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.professor.escola):
            return _negar(request, "Sem permissão para esta escola.")
        if novo.ativo:
            ProfessorUsuario.objects.filter(
                professor=novo.professor, ativo=True
            ).exclude(pk=novo.pk).update(ativo=False, data_fim=date.today())
        novo.save()
        messages.success(request, "Vínculo atualizado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/form.html", {"form": form, "titulo": "Editar Vínculo"})


@admin_estrito_required
def vinculo_encerrar(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return _negar(request, "Sem permissão para encerrar este vínculo.")
    if request.method == "POST":
        obj.encerrar()
        messages.success(request, "Vínculo encerrado.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/confirm_encerrar.html", {"obj": obj, "titulo": "Encerrar Vínculo"})


@admin_estrito_required
def vinculo_delete(request, pk):
    obj = get_object_or_404(ProfessorUsuario, pk=pk)
    if not pode_administrar_escola(request.user, obj.professor.escola):
        return _negar(request, "Sem permissão para excluir este vínculo.")
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Vínculo excluído.")
        return redirect("cal:vinculo_list")
    return render(request, "diario/professor_usuario/confirm_delete.html", {"obj": obj, "titulo": "Excluir Vínculo"})
