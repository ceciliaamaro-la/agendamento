from collections import defaultdict
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from ..models import Horario, Turma, Dias, OrdemHorario
from ..forms import HorarioForm
from ..services.escopo import (
    admin_escola_required, admin_estrito_required, _negar,
    filtrar_por_escola, pode_administrar_escola,
    turmas_do_usuario, escolas_administradas, horarios_do_usuario,
    is_admin_escola, is_coordenador,
)


@login_required
def horario_list(request):
    turma_id = request.GET.get("turma")
    qs = horarios_do_usuario(request.user).select_related(
        "escola", "turma", "turma__escola", "dia", "ordem", "professor", "materia"
    )
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    qs = qs.order_by("turma__escola__nome_escola", "turma__nome_turma", "dia__ordem", "ordem__posicao", "ordem__id")

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
        ordens.sort(key=lambda o: (o.posicao, o.id))
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

    turmas = turmas_do_usuario(request.user).select_related("escola").order_by("escola__nome_escola", "nome_turma")
    return render(request, "diario/horario/list.html", {
        "escolas": dict(escolas),
        "tem_horarios": qs.exists(),
        "turmas": turmas,
        "turma_filtro": turma_id,
        "pode_admin": is_admin_escola(request.user) and not is_coordenador(request.user),
    })


@admin_estrito_required
def horario_create(request):
    form = HorarioForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        h = form.save(commit=False)
        if not pode_administrar_escola(request.user, h.turma.escola):
            return _negar(request, "Sem permissão para esta escola.")
        h.save()
        messages.success(request, "Horário cadastrado.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/form.html", {"form": form, "titulo": "Novo Horário"})


@admin_estrito_required
def horario_update(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    if not pode_administrar_escola(request.user, horario.turma.escola):
        return _negar(request, "Sem permissão para editar este horário.")
    form = HorarioForm(request.POST or None, instance=horario, user=request.user)
    if request.method == "POST" and form.is_valid():
        h = form.save(commit=False)
        if not pode_administrar_escola(request.user, h.turma.escola):
            return _negar(request, "Escola fora do seu escopo.")
        h.save()
        messages.success(request, "Horário atualizado.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/form.html", {"form": form, "titulo": "Editar Horário"})


@login_required
def horario_pdf(request):
    from datetime import date
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
        HRFlowable,
    )
    from ..services.pdf_utils import cabecalho_pdf

    turma_id = request.GET.get("turma")
    qs = Horario.objects.select_related(
        "escola", "turma", "turma__escola", "dia", "ordem", "professor", "materia"
    )
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    qs = qs.order_by("turma__escola__nome_escola", "turma__nome_turma", "dia__ordem", "ordem__posicao", "ordem__id")

    # Agrupa por (escola, turma) → dict[(ordem_id, dia_id)] = horario
    grupos = defaultdict(dict)
    turmas_meta = {}
    ordens_usadas = defaultdict(dict)  # key -> {ordem_id: ordem_obj}
    escolas_obj = {}
    turmas_obj = {}
    for h in qs:
        key = (h.turma.escola_id, h.turma_id)
        grupos[key][(h.ordem_id, h.dia_id)] = h
        turmas_meta[key] = (h.turma.escola.nome_escola, h.turma.nome_turma)
        ordens_usadas[key][h.ordem_id] = h.ordem
        escolas_obj[key] = h.turma.escola
        turmas_obj[key] = h.turma

    dias = list(Dias.objects.order_by("ordem"))

    buf = BytesIO()
    PAGE_W = landscape(A4)[0]
    margem = 1.2 * cm
    largura_util = PAGE_W - 2 * margem
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=margem, rightMargin=margem,
        topMargin=margem, bottomMargin=margem,
        title="Horários",
    )
    styles = getSampleStyleSheet()
    sub_style = ParagraphStyle("sub", parent=styles["Heading4"], spaceAfter=4, textColor=colors.HexColor("#444"))
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10, alignment=1)
    head_style = ParagraphStyle("head", parent=styles["Normal"], fontSize=9, leading=11, alignment=1, textColor=colors.white)
    rodape_style = ParagraphStyle("rodape", parent=styles["Normal"], fontSize=7,
                                  textColor=colors.HexColor("#6c757d"), alignment=1)

    story = []
    if not grupos:
        story.append(Paragraph("Nenhum horário encontrado para o filtro atual.", styles["Normal"]))

    for i, (key, celulas) in enumerate(grupos.items()):
        escola_nome, turma_nome = turmas_meta[key]
        escola = escolas_obj[key]
        turma = turmas_obj[key]
        turno_disp = turma.get_turno_display() if getattr(turma, "turno", "") else ""
        subtitulos = [
            f"Grade de <b>Horários</b> — Turma <b>{turma_nome}</b>"
            + (f" ({turno_disp})" if turno_disp else ""),
            f"Emitido em {date.today().strftime('%d/%m/%Y')}",
        ]
        story.append(cabecalho_pdf(escola, escola_nome or "Escola", subtitulos, largura_util))
        story.append(Spacer(1, 0.15 * cm))
        story.append(HRFlowable(width="100%", thickness=1.2,
                                color=colors.HexColor("#0d6efd"),
                                spaceBefore=0, spaceAfter=0.3 * cm))

        # Apenas ordens realmente registradas para esta turma
        ordens = sorted(ordens_usadas[key].values(), key=lambda o: (o.posicao, o.id))

        # Cabeçalho: vazio + dias
        header = [Paragraph("<b>Horário</b>", head_style)] + [
            Paragraph(f"<b>{d.dias}</b>", head_style) for d in dias
        ]
        rows = [header]
        for o in ordens:
            label = f"<b>{o.ordem}</b>"
            if o.faixa:
                label += f"<br/><font size=6 color='#888'>{o.faixa}</font>"
            row = [Paragraph(label, cell_style)]
            for d in dias:
                h = celulas.get((o.id, d.id))
                if h:
                    if h.materia and h.professor:
                        txt = f"<b>{h.materia}</b><br/><font size=7 color='#555'>{h.professor}</font>"
                    elif h.materia:
                        txt = f"<b>{h.materia}</b>"
                    else:
                        txt = f"<i><font color='#666'>{h.ordem}</font></i>"
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


@admin_estrito_required
def horario_delete(request, pk):
    horario = get_object_or_404(Horario, pk=pk)
    if not pode_administrar_escola(request.user, horario.turma.escola):
        return _negar(request, "Sem permissão para excluir este horário.")
    if request.method == "POST":
        horario.delete()
        messages.success(request, "Horário excluído.")
        return redirect("cal:horario_list")
    return render(request, "diario/horario/confirm_delete.html", {"obj": horario, "titulo": "Excluir Horário"})
