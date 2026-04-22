from collections import defaultdict
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from ..models import Horario, Turma, Dias, OrdemHorario
from ..forms import HorarioForm


@login_required
def horario_list(request):
    turma_id = request.GET.get("turma")
    qs = Horario.objects.select_related(
        "escola", "turma", "turma__escola", "dia", "ordem", "professor", "materia"
    )
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    qs = qs.order_by("turma__escola__nome_escola", "turma__nome_turma", "dia__ordem", "ordem__id")

    dias_all = list(Dias.objects.order_by("ordem"))

    # Agrupa: escola → [turmas]; turma → grid (ordens reais x dias) usados
    grupos_tmp = defaultdict(dict)  # (escola_id, turma_id) -> celulas {(ordem_id, dia_id): h}
    meta = {}
    ordens_por_turma = defaultdict(dict)  # mantém ordem de inserção por id
    for h in qs:
        key = (h.turma.escola_id, h.turma_id)
        grupos_tmp[key][(h.ordem_id, h.dia_id)] = h
        meta[key] = (h.turma.escola.nome_escola, h.turma.nome_turma)
        ordens_por_turma[key][h.ordem_id] = h.ordem

    # Monta estrutura: escola -> [turmas com grid]
    escolas = defaultdict(list)
    for key, celulas in grupos_tmp.items():
        escola_nome, turma_nome = meta[key]
        ordens = list(ordens_por_turma[key].values())
        ordens.sort(key=lambda o: o.id)
        linhas = []
        for o in ordens:
            linhas.append({
                "ordem": o,
                "celulas": [celulas.get((o.id, d.id)) for d in dias_all],
            })
        escolas[escola_nome].append({
            "nome": turma_nome,
            "dias": dias_all,
            "linhas": linhas,
        })

    turmas = Turma.objects.select_related("escola").order_by("escola__nome_escola", "nome_turma")
    return render(request, "diario/horario/list.html", {
        "escolas": dict(escolas),
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
def horario_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )

    turma_id = request.GET.get("turma")
    qs = Horario.objects.select_related(
        "escola", "turma", "turma__escola", "dia", "ordem", "professor", "materia"
    )
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    qs = qs.order_by("turma__escola__nome_escola", "turma__nome_turma", "dia__ordem", "ordem__id")

    # Agrupa por (escola, turma) → dict[(ordem_id, dia_id)] = horario
    grupos = defaultdict(dict)
    turmas_meta = {}
    for h in qs:
        key = (h.turma.escola_id, h.turma_id)
        grupos[key][(h.ordem_id, h.dia_id)] = h
        turmas_meta[key] = (h.turma.escola.nome_escola, h.turma.nome_turma)

    dias = list(Dias.objects.order_by("ordem"))
    ordens = list(OrdemHorario.objects.order_by("id"))

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
        title="Horários",
    )
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle("h", parent=styles["Heading2"], spaceAfter=6, textColor=colors.HexColor("#1a3a6c"))
    sub_style = ParagraphStyle("sub", parent=styles["Heading4"], spaceAfter=4, textColor=colors.HexColor("#444"))
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10, alignment=1)
    head_style = ParagraphStyle("head", parent=styles["Normal"], fontSize=9, leading=11, alignment=1, textColor=colors.white)

    story = []
    if not grupos:
        story.append(Paragraph("Nenhum horário encontrado para o filtro atual.", styles["Normal"]))

    for i, (key, celulas) in enumerate(grupos.items()):
        escola_nome, turma_nome = turmas_meta[key]
        story.append(Paragraph(f"🏫 {escola_nome}", h_style))
        story.append(Paragraph(f"Turma: <b>{turma_nome}</b>", sub_style))

        # Cabeçalho: vazio + dias
        header = [Paragraph("<b>Horário</b>", head_style)] + [
            Paragraph(f"<b>{d.dias}</b>", head_style) for d in dias
        ]
        rows = [header]
        for o in ordens:
            row = [Paragraph(f"<b>{o.ordem}</b>", cell_style)]
            for d in dias:
                h = celulas.get((o.id, d.id))
                if h:
                    txt = f"<b>{h.materia}</b><br/><font size=7 color='#555'>{h.professor}</font>"
                else:
                    txt = "<font color='#bbb'>—</font>"
                row.append(Paragraph(txt, cell_style))
            rows.append(row)

        col_w = [2.2 * cm] + [(27.7 - 2.2) / len(dias) * cm] * len(dias)
        tbl = Table(rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a6c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f0f3f8")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfd")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))
        if i < len(grupos) - 1:
            story.append(PageBreak())

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()

    sufixo = "todas-turmas"
    if turma_id:
        t = Turma.objects.filter(pk=turma_id).first()
        if t:
            sufixo = f"{t.escola.nome_escola}-{t.nome_turma}".replace(" ", "_")

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="horarios-{sufixo}.pdf"'
    return resp


@login_required
def horario_delete(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    if request.method == "POST":
        horario.delete()
        messages.success(request, "Horário excluído.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/confirm_delete.html", {"obj": horario, "titulo": "Excluir Horário"})
