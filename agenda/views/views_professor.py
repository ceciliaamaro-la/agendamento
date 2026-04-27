from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import Professor
from ..forms import ProfessorForm
from ..services.escopo import (
    admin_escola_required, admin_estrito_required, _negar,
    filtrar_por_escola, pode_administrar_escola,
    escolas_administradas, is_admin_escola, bloquear_alunos_responsaveis,
    escolas_do_usuario, is_coordenador,
)


@bloquear_alunos_responsaveis
def professor_list(request):
    base = Professor.objects.select_related("escola", "materia").all()
    if is_admin_escola(request.user):
        professores = filtrar_por_escola(base, request.user)
    else:
        # Professor: lê todos das escolas visíveis
        professores = base.filter(escola__in=escolas_do_usuario(request.user))
    professores = professores.order_by("escola__nome_escola", "nome_professor")
    return render(request, "diario/professor/list.html", {
        "professores": professores,
        "pode_admin": is_admin_escola(request.user) and not is_coordenador(request.user),
    })


def _form_com_escopo(request, instance=None):
    form = ProfessorForm(request.POST or None, instance=instance)
    form.fields["escola"].queryset = escolas_administradas(request.user)
    qs = form.fields["escola"].queryset
    if qs.count() == 1:
        unica = qs.first()
        form.fields["escola"].initial = unica.id
        form.fields["escola"].disabled = True
        form.fields["escola"].help_text = "Sua escola foi selecionada automaticamente."
        if not form.is_bound and not form.initial.get("escola"):
            form.initial["escola"] = unica.id
    return form


@admin_estrito_required
def professor_create(request):
    form = _form_com_escopo(request)
    if request.method == "POST" and form.is_valid():
        prof = form.save(commit=False)
        if not pode_administrar_escola(request.user, prof.escola):
            return _negar(request, "Sem permissão para esta escola.")
        prof.save()
        messages.success(request, "Professor(a) cadastrado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Novo Professor"})


@admin_estrito_required
def professor_update(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    if not pode_administrar_escola(request.user, professor.escola):
        return _negar(request, "Sem permissão para editar este professor.")
    form = _form_com_escopo(request, instance=professor)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.escola):
            return _negar(request, "Escola fora do seu escopo.")
        novo.save()
        messages.success(request, "Professor(a) atualizado(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/form.html", {"form": form, "titulo": "Editar Professor"})


@admin_estrito_required
def professor_delete(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    if not pode_administrar_escola(request.user, professor.escola):
        return _negar(request, "Sem permissão para excluir este professor.")
    if request.method == "POST":
        professor.delete()
        messages.success(request, "Professor(a) excluído(a).")
        return redirect("cal:professor_list")
    return render(request, "diario/professor/confirm_delete.html", {"obj": professor, "titulo": "Excluir Professor"})
