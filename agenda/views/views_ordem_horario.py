"""Períodos (Ordem de Horário) são globais. Apenas super-admin gerencia."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from ..models import OrdemHorario
from ..forms import OrdemHorarioForm
from ..services.escopo import (
    admin_escola_required, superadmin_required, bloquear_alunos_responsaveis,
    is_superadmin,
)


@bloquear_alunos_responsaveis
def ordem_list(request):
    ordens = OrdemHorario.objects.all().order_by("turno", "posicao", "id")

    # Agrupa por turno para exibir uma seção por turno
    from collections import OrderedDict
    rotulos = dict(OrdemHorario.TURNO_CHOICES)
    grupos = OrderedDict()
    # Garante a ordem dos blocos: M, V, N, I, e por último os "comuns"
    for sigla in ("M", "V", "N", "I", ""):
        grupos[sigla] = {
            "rotulo": rotulos.get(sigla, "Comum a todos os turnos"),
            "itens": [],
        }
    for o in ordens:
        chave = o.turno or ""
        grupos.setdefault(chave, {"rotulo": rotulos.get(chave, "Comum"), "itens": []})
        grupos[chave]["itens"].append(o)

    # Remove blocos vazios
    grupos = {k: v for k, v in grupos.items() if v["itens"]}

    return render(request, "diario/ordem_horario/list.html", {
        "ordens": ordens,
        "grupos": grupos,
        "pode_admin": is_superadmin(request.user),
    })


@admin_escola_required
def ordem_create(request):
    form = OrdemHorarioForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Período cadastrado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Novo Período"})


@admin_escola_required
def ordem_update(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    form = OrdemHorarioForm(request.POST or None, instance=ordem)
    if form.is_valid():
        form.save()
        messages.success(request, "Período atualizado.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/form.html", {"form": form, "titulo": "Editar Período"})


@admin_escola_required
def ordem_delete(request, pk):
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if request.method == "POST":
        ordem.delete()
        messages.success(request, "Período excluído.")
        return redirect("cal:ordem_list")
    return render(request, "diario/ordem_horario/confirm_delete.html", {"obj": ordem, "titulo": "Excluir Período"})


def _normalizar_posicoes():
    """Garante que todos os períodos tenham posições sequenciais 1..N
    respeitando a ordem atual (posicao, id)."""
    for i, o in enumerate(OrdemHorario.objects.order_by("posicao", "id"), start=1):
        if o.posicao != i:
            OrdemHorario.objects.filter(pk=o.pk).update(posicao=i)


@admin_escola_required
def ordem_mover(request, pk, direcao):
    """Move um período para cima ou para baixo trocando posições com o vizinho."""
    _normalizar_posicoes()
    ordem = get_object_or_404(OrdemHorario, pk=pk)
    if direcao == "cima":
        vizinho = OrdemHorario.objects.filter(posicao__lt=ordem.posicao).order_by("-posicao").first()
    else:
        vizinho = OrdemHorario.objects.filter(posicao__gt=ordem.posicao).order_by("posicao").first()
    if vizinho:
        p1, p2 = ordem.posicao, vizinho.posicao
        OrdemHorario.objects.filter(pk=ordem.pk).update(posicao=p2)
        OrdemHorario.objects.filter(pk=vizinho.pk).update(posicao=p1)
    return redirect("cal:ordem_list")
