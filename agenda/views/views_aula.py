from collections import defaultdict
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, DateField
from django.db.models.functions import Coalesce, Cast
from ..models import Aula, Turma, DiarioAluno, Aluno
from ..forms import AulaForm, DiarioAlunoFormSet
from ..services.aula_evento_sync import sincronizar_evento_da_aula
from ..services.escopo import (
    aulas_do_usuario,
    pode_editar_aula,
    is_admin_escola,
    is_superadmin,
    professor_do_usuario,
    turmas_do_usuario,
    _negar,
)


def _aula_ou_403(request, pk):
    """Busca a aula respeitando o escopo do usuário; redireciona com mensagem se não autorizado."""
    aula = get_object_or_404(Aula, pk=pk)
    if not pode_editar_aula(request.user, aula):
        return None, _negar(
            request, "Você não tem permissão para acessar esta aula."
        )
    return aula, None


@login_required
def aula_list(request):
    from ..services.agrupamento import estruturar

    turma_id = request.GET.get("turma")
    qs = aulas_do_usuario(request.user).select_related(
        "escola", "turma", "turma__escola", "professor", "materia"
    ).annotate(
        data_ordem=Coalesce("data_entrega", Cast("criado_em", output_field=DateField()))
    ).order_by("escola__nome_escola", "turma__nome_turma", "materia__nome_materia", "data_ordem")

    if turma_id:
        qs = qs.filter(turma_id=turma_id)

    triples = []
    for aula in qs:
        dias = aula.dias_para_entrega()
        if dias is not None:
            aula.cor = "danger" if dias <= 1 else ("warning" if dias <= 3 else "success")
        else:
            aula.cor = "secondary"
        esc_nome = aula.escola.nome_escola if aula.escola else (
            aula.turma.escola.nome_escola if aula.turma and aula.turma.escola else None
        )
        triples.append((esc_nome, aula.turma, aula.materia, aula))

    escolas = estruturar(triples, sem_materia_label="Sem matéria", sem_materia_icon="dash-circle")

    turmas = turmas_do_usuario(request.user).select_related("escola").order_by(
        "escola__nome_escola", "nome_turma"
    )
    return render(request, "diario/aula/list.html", {
        "escolas": escolas,
        "tem_aulas": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
        "hoje": date.today(),
        "is_admin": is_admin_escola(request.user),
    })


@login_required
def aula_create(request):
    initial = {}
    ultima_turma = request.session.get("ultima_turma_id")
    if ultima_turma:
        initial["turma"] = ultima_turma
    form = AulaForm(request.POST or None, user=request.user, initial=initial)
    if form.is_valid():
        aula = form.save(commit=False)
        # Garante que professor não-admin não burle o "disabled" via POST
        if not is_admin_escola(request.user):
            prof = professor_do_usuario(request.user)
            if prof is not None:
                aula.professor = prof
        aula.save()
        request.session["ultima_turma_id"] = aula.turma_id
        sincronizar_evento_da_aula(aula)
        messages.success(request, "Aula cadastrada e publicada na agenda. Faça a chamada agora.")
        return redirect("cal:diario_chamada", pk=aula.pk)
    return render(request, "diario/aula/form.html", {"form": form, "titulo": "Nova Aula / Dever"})


@login_required
def aula_update(request, pk):
    aula, forbidden = _aula_ou_403(request, pk)
    if forbidden:
        return forbidden
    form = AulaForm(request.POST or None, instance=aula, user=request.user)
    if form.is_valid():
        aula = form.save(commit=False)
        if not is_admin_escola(request.user):
            prof = professor_do_usuario(request.user)
            if prof is not None:
                aula.professor = prof
        aula.save()
        request.session["ultima_turma_id"] = aula.turma_id
        sincronizar_evento_da_aula(aula)
        messages.success(request, "Aula atualizada (e evento da agenda sincronizado).")
        return redirect("cal:aula_list")
    return render(request, "diario/aula/form.html", {"form": form, "titulo": "Editar Aula"})


@login_required
def aula_delete(request, pk):
    aula, forbidden = _aula_ou_403(request, pk)
    if forbidden:
        return forbidden
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
    aula, forbidden = _aula_ou_403(request, pk)
    if forbidden:
        return forbidden

    alunos_turma = list(
        Aluno.objects.filter(turma=aula.turma).order_by("nome_aluno")
    )

    # Bulk: cria registros faltantes em UMA query (em vez de N get_or_create)
    existentes_ids = set(
        DiarioAluno.objects.filter(aula=aula).values_list("aluno_id", flat=True)
    )
    faltando = [a for a in alunos_turma if a.id not in existentes_ids]
    if faltando:
        DiarioAluno.objects.bulk_create(
            [DiarioAluno(aula=aula, aluno=a) for a in faltando],
            ignore_conflicts=True,
        )

    if request.method == "POST":
        formset = DiarioAlunoFormSet(request.POST, instance=aula)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Chamada registrada.")
            return redirect("cal:diario_list")
        messages.error(request, "Erro ao salvar a chamada.")
    else:
        formset = DiarioAlunoFormSet(instance=aula)

    # Mapeia em UMA query e monta os registros
    diarios_map = {
        d.aluno_id: d
        for d in DiarioAluno.objects.filter(aula=aula).select_related("aluno")
    }
    registros = list(zip(
        formset.forms,
        [diarios_map.get(a.id) for a in alunos_turma],
        alunos_turma,
    ))

    return render(request, "diario/chamada/chamada.html", {
        "aula": aula,
        "formset": formset,
        "registros": registros,
    })


@login_required
def diario_list(request):
    from ..services.agrupamento import estruturar

    turma_id = request.GET.get("turma")
    qs = aulas_do_usuario(request.user).select_related(
        "turma", "turma__escola", "materia", "professor"
    ).annotate(
        total_alunos=Count("diario", distinct=True),
        total_faltas=Count("diario", filter=Q(diario__presente=False), distinct=True),
    ).order_by("-data_aula", "-criado_em")

    if turma_id:
        qs = qs.filter(turma_id=turma_id)

    triples = []
    for aula in qs:
        esc_nome = aula.turma.escola.nome_escola if aula.turma and aula.turma.escola else None
        triples.append((esc_nome, aula.turma, aula.materia, aula))

    escolas = estruturar(triples, sem_materia_label="Sem matéria", sem_materia_icon="dash-circle")

    turmas = turmas_do_usuario(request.user).select_related("escola").order_by(
        "escola__nome_escola", "nome_turma"
    )
    return render(request, "diario/chamada/list.html", {
        "escolas": escolas,
        "tem_aulas": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
    })


@login_required
def diario_detail(request, pk):
    aula, forbidden = _aula_ou_403(request, pk)
    if forbidden:
        return forbidden
    registros = (
        DiarioAluno.objects.filter(aula=aula)
        .select_related("aluno")
        .order_by("aluno__nome_aluno")
    )
    # Conta presenças/ausências em UMA query (em vez de 3)
    counts = registros.aggregate(
        total=Count("id"),
        presentes=Count("id", filter=Q(presente=True)),
        ausentes=Count("id", filter=Q(presente=False)),
    )
    return render(request, "diario/chamada/detail.html", {
        "aula": aula,
        "registros": registros,
        "presentes": counts["presentes"],
        "ausentes": counts["ausentes"],
        "total": counts["total"],
    })
