from collections import defaultdict
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.db.models.functions import Coalesce, Cast
from django.db.models import DateField

from ..models import Aula, Escola, Turma, DiarioAluno, Aluno
from ..forms import AulaForm, DiarioAlunoFormSet
from ..services.aula_evento_sync import sincronizar_evento_da_aula


@login_required
def aula_list(request):
    turma_id = request.GET.get("turma")
    qs = Aula.objects.select_related(
        "escola", "turma", "professor", "materia"
    ).annotate(
        data_ordem=Coalesce("data_entrega", Cast("criado_em", output_field=DateField()))
    ).order_by("escola__nome_escola", "turma__nome_turma", "data_ordem")

    if turma_id:
        qs = qs.filter(turma_id=turma_id)

    # Agrupa: escola → turma → [aulas]
    agrupado = defaultdict(lambda: defaultdict(list))
    hoje = date.today()
    for aula in qs:
        dias = aula.dias_para_entrega()
        if dias is not None:
            aula.cor = "danger" if dias <= 1 else ("warning" if dias <= 3 else "success")
        else:
            aula.cor = "secondary"
        agrupado[aula.escola.nome_escola][aula.turma.nome_turma].append(aula)

    def to_dict(d):
        return {k: to_dict(v) for k, v in d.items()} if isinstance(d, defaultdict) else d

    turmas = Turma.objects.select_related("escola").order_by("escola__nome_escola", "nome_turma")
    return render(request, "diario/aula/list.html", {
        "agrupado": to_dict(agrupado),
        "tem_aulas": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
        "hoje": hoje,
    })


@login_required
def aula_create(request):
    form = AulaForm(request.POST or None)
    if form.is_valid():
        aula = form.save()
        sincronizar_evento_da_aula(aula)
        messages.success(request, "Aula cadastrada e publicada na agenda. Faça a chamada agora.")
        return redirect("cal:diario_chamada", pk=aula.pk)
    return render(request, "diario/aula/form.html", {"form": form, "titulo": "Nova Aula / Dever"})


@login_required
def aula_update(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    form = AulaForm(request.POST or None, instance=aula)
    if form.is_valid():
        aula = form.save()
        sincronizar_evento_da_aula(aula)
        messages.success(request, "Aula atualizada (e evento da agenda sincronizado).")
        return redirect("cal:aula_list")
    return render(request, "diario/aula/form.html", {"form": form, "titulo": "Editar Aula"})


@login_required
def aula_delete(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    if request.method == "POST":
        aula.delete()
        messages.success(request, "Aula excluída.")
        return redirect("cal:aula_list")
    return render(request, "diario/aula/confirm_delete.html", {"obj": aula, "titulo": "Excluir Aula"})


# ---------------------------------------------------------------------------
# Diário de chamada
# ---------------------------------------------------------------------------

@login_required
def diario_chamada(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    alunos_turma = Aluno.objects.filter(turma=aula.turma).order_by("nome_aluno")

    # Garante registro para cada aluno da turma
    for aluno in alunos_turma:
        DiarioAluno.objects.get_or_create(aula=aula, aluno=aluno)

    if request.method == "POST":
        formset = DiarioAlunoFormSet(request.POST, instance=aula)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Chamada registrada.")
            return redirect("cal:diario_list")
        messages.error(request, "Erro ao salvar a chamada.")
    else:
        formset = DiarioAlunoFormSet(instance=aula)

    registros = list(zip(
        formset.forms,
        [DiarioAluno.objects.get(aula=aula, aluno=a) for a in alunos_turma],
        alunos_turma,
    ))

    return render(request, "diario/chamada/chamada.html", {
        "aula": aula,
        "formset": formset,
        "registros": registros,
    })


@login_required
def diario_list(request):
    turma_id = request.GET.get("turma")
    qs = Aula.objects.select_related(
        "turma", "turma__escola", "materia", "professor"
    ).order_by("-data_aula", "-criado_em")

    if turma_id:
        qs = qs.filter(turma_id=turma_id)

    aulas_por_escola = defaultdict(lambda: defaultdict(list))
    for aula in qs:
        total = DiarioAluno.objects.filter(aula=aula).count()
        faltas = DiarioAluno.objects.filter(aula=aula, presente=False).count()
        aula.total_alunos = total
        aula.total_faltas = faltas
        aulas_por_escola[aula.turma.escola.nome_escola][aula.turma.nome_turma].append(aula)

    def to_dict(d):
        return {k: to_dict(v) for k, v in d.items()} if isinstance(d, defaultdict) else d

    turmas = Turma.objects.select_related("escola").order_by("escola__nome_escola", "nome_turma")
    return render(request, "diario/chamada/list.html", {
        "aulas_por_escola": to_dict(aulas_por_escola),
        "tem_aulas": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
    })


@login_required
def diario_detail(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    registros = DiarioAluno.objects.filter(aula=aula).select_related("aluno").order_by("aluno__nome_aluno")
    return render(request, "diario/chamada/detail.html", {
        "aula": aula,
        "registros": registros,
        "presentes": registros.filter(presente=True).count(),
        "ausentes": registros.filter(presente=False).count(),
        "total": registros.count(),
    })
