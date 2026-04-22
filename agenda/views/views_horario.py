from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Horario, Turma
from ..forms import HorarioForm


@login_required
def horario_list(request):
    turma_id = request.GET.get("turma")
    qs = Horario.objects.select_related(
        "escola", "turma", "turma__escola", "dia", "ordem", "professor", "materia"
    ).order_by("turma__escola__nome_escola", "turma__nome_turma", "dia__ordem", "ordem")

    if turma_id:
        qs = qs.filter(turma_id=turma_id)

    # Agrupa: escola → turma → dia → [horários]
    agrupado = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for h in qs:
        agrupado[h.escola.nome_escola][h.turma.nome_turma][h.dia.dias].append(h)

    def to_dict(d):
        return {k: to_dict(v) for k, v in d.items()} if isinstance(d, defaultdict) else d

    turmas = Turma.objects.select_related("escola").order_by("escola__nome_escola", "nome_turma")
    return render(request, "diario/horario/list.html", {
        "agrupado": to_dict(agrupado),
        "tem_horarios": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
    })


@login_required
def horario_create(request):
    form = HorarioForm(request.POST or None, user=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Horário cadastrado.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/form.html", {"form": form, "titulo": "Novo Horário"})


@login_required
def horario_update(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    form = HorarioForm(request.POST or None, instance=horario, user=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Horário atualizado.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/form.html", {"form": form, "titulo": "Editar Horário"})


@login_required
def horario_delete(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    if request.method == "POST":
        horario.delete()
        messages.success(request, "Horário excluído.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/confirm_delete.html", {"obj": horario, "titulo": "Excluir Horário"})
