from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from ..models import Monitoria, Escola, Dias
from ..forms import MonitoriaForm
from ..services.escopo import (
    admin_estrito_required, filtrar_por_escola, pode_administrar_escola,
    escolas_administradas, is_superadmin, papel_de,
)
from ..models import PerfilUsuario


def _pode_editar_monitoria(user):
    return is_superadmin(user) or papel_de(user) == PerfilUsuario.PAPEL_ADMIN_ESCOLA


@login_required
def monitoria_programacao(request):
    """Página pública (a todos os logados): exibe a programação no formato
    pivotado por professor × dia da semana, semelhante ao modelo da imagem."""
    monitorias = filtrar_por_escola(
        Monitoria.objects.filter(ativo=True)
        .select_related("escola", "professor", "materia", "dia"),
        request.user,
    )

    dias = list(Dias.objects.all().order_by("ordem", "id"))

    # Agrupa por escola → (professor, materia) → {dia_id: [monitorias]}
    escolas_dict = {}
    for m in monitorias:
        esc_key = (m.escola_id, m.escola.nome_escola if m.escola else "—")
        prof_key = (m.professor_id, m.professor.nome_professor, m.materia_id, m.materia.nome_materia)
        escolas_dict.setdefault(esc_key, {}).setdefault(prof_key, {}).setdefault(m.dia_id, []).append(m)

    escolas = []
    for (esc_id, esc_nome), profs in sorted(escolas_dict.items(), key=lambda x: x[0][1] or ""):
        linhas = []
        for (prof_id, prof_nome, mat_id, mat_nome), por_dia in sorted(profs.items(), key=lambda x: x[0][1]):
            celulas = [{"dia": d, "items": por_dia.get(d.id, [])} for d in dias]
            linhas.append({
                "professor": prof_nome,
                "materia": mat_nome,
                "celulas": celulas,
            })
        escolas.append({"nome": esc_nome, "linhas": linhas})

    return render(request, "diario/monitoria/programacao.html", {
        "escolas": escolas,
        "dias": dias,
        "pode_admin": _pode_editar_monitoria(request.user),
    })


@admin_estrito_required
def monitoria_list(request):
    monitorias = filtrar_por_escola(
        Monitoria.objects.select_related("escola", "professor", "materia", "dia").all(),
        request.user,
    )
    return render(request, "diario/monitoria/list.html", {"monitorias": monitorias})


def _form_com_escopo(request, instance=None):
    form = MonitoriaForm(request.POST or None, instance=instance)
    form.fields["escola"].queryset = escolas_administradas(request.user)
    return form


@admin_estrito_required
def monitoria_create(request):
    form = _form_com_escopo(request)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not pode_administrar_escola(request.user, obj.escola):
            return HttpResponseForbidden("Sem permissão para esta escola.")
        obj.save()
        messages.success(request, "Monitoria cadastrada.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/form.html", {"form": form, "titulo": "Nova Monitoria"})


@admin_estrito_required
def monitoria_update(request, pk):
    obj = get_object_or_404(Monitoria, pk=pk)
    if not pode_administrar_escola(request.user, obj.escola):
        return HttpResponseForbidden("Sem permissão.")
    form = _form_com_escopo(request, instance=obj)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if not pode_administrar_escola(request.user, novo.escola):
            return HttpResponseForbidden("Escola fora do seu escopo.")
        novo.save()
        messages.success(request, "Monitoria atualizada.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/form.html", {"form": form, "titulo": "Editar Monitoria"})


@admin_estrito_required
def monitoria_delete(request, pk):
    obj = get_object_or_404(Monitoria, pk=pk)
    if not pode_administrar_escola(request.user, obj.escola):
        return HttpResponseForbidden("Sem permissão.")
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Monitoria excluída.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/confirm_delete.html", {"obj": obj, "titulo": "Excluir Monitoria"})
