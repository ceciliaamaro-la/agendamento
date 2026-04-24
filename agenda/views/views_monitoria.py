from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse

from ..models import Monitoria, Escola, Dias
from ..forms import MonitoriaForm
from ..services.escopo import (
    admin_estrito_required, filtrar_por_escola, pode_administrar_escola,
    escolas_administradas, escolas_do_usuario, is_superadmin, papel_de,
    is_admin_escola, is_professor, professor_do_usuario,
    professor_ou_admin_required,
)
from ..models import PerfilUsuario


def _pode_editar_monitoria(user, monitoria=None):
    """admin_escola edita as da escola dele; professor só as próprias."""
    if is_superadmin(user) or is_admin_escola(user):
        if monitoria is None:
            return True
        return pode_administrar_escola(user, monitoria.escola)
    if is_professor(user):
        if monitoria is None:
            return True
        prof = professor_do_usuario(user)
        return bool(prof and monitoria.professor_id == prof.id)
    return False


@login_required
def monitoria_programacao(request):
    """Página pública (a todos os logados): exibe a programação no formato
    pivotado por professor × dia da semana, semelhante ao modelo da imagem."""
    # Programação visível a TODOS os logados (alunos/responsáveis inclusive),
    # restrita à(s) escola(s) visíveis.
    monitorias = (
        Monitoria.objects.filter(ativo=True, escola__in=escolas_do_usuario(request.user))
        .select_related("escola", "professor", "materia", "dia")
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
        # Apenas dias com pelo menos 1 monitoria nesta escola
        dias_ids_usados = {d_id for por_dia in profs.values() for d_id in por_dia.keys()}
        dias_usados = [d for d in dias if d.id in dias_ids_usados]

        linhas = []
        for (prof_id, prof_nome, mat_id, mat_nome), por_dia in sorted(profs.items(), key=lambda x: x[0][1]):
            celulas = [{"dia": d, "items": por_dia.get(d.id, [])} for d in dias_usados]
            linhas.append({
                "professor": prof_nome,
                "materia": mat_nome,
                "celulas": celulas,
            })
        escolas.append({"nome": esc_nome, "dias": dias_usados, "linhas": linhas})

    return render(request, "diario/monitoria/programacao.html", {
        "escolas": escolas,
        "pode_admin": _pode_editar_monitoria(request.user),
    })


@professor_ou_admin_required
def monitoria_list(request):
    base = Monitoria.objects.select_related("escola", "professor", "materia", "dia").all()
    if is_admin_escola(request.user):
        monitorias = filtrar_por_escola(base, request.user)
    else:
        prof = professor_do_usuario(request.user)
        monitorias = base.filter(professor=prof) if prof else base.none()
    return render(request, "diario/monitoria/list.html", {
        "monitorias": monitorias,
        "pode_admin_geral": is_admin_escola(request.user),
    })


def _form_com_escopo(request, instance=None):
    form = MonitoriaForm(request.POST or None, instance=instance)
    if is_admin_escola(request.user):
        form.fields["escola"].queryset = escolas_administradas(request.user)
    else:
        # professor: limita escola e professor às próprias
        form.fields["escola"].queryset = escolas_do_usuario(request.user)
        prof = professor_do_usuario(request.user)
        if prof:
            from ..models import Professor as _P
            form.fields["professor"].queryset = _P.objects.filter(pk=prof.pk)
            form.fields["professor"].initial = prof
            form.fields["professor"].disabled = True
    return form


@professor_ou_admin_required
def monitoria_create(request):
    form = _form_com_escopo(request)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if is_professor(request.user) and not is_admin_escola(request.user):
            obj.professor = professor_do_usuario(request.user)
        if not _pode_editar_monitoria(request.user, obj):
            return HttpResponseForbidden("Sem permissão para esta monitoria.")
        obj.save()
        messages.success(request, "Monitoria cadastrada.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/form.html", {"form": form, "titulo": "Nova Monitoria"})


@professor_ou_admin_required
def monitoria_update(request, pk):
    obj = get_object_or_404(Monitoria, pk=pk)
    if not _pode_editar_monitoria(request.user, obj):
        return HttpResponseForbidden("Sem permissão.")
    form = _form_com_escopo(request, instance=obj)
    if request.method == "POST" and form.is_valid():
        novo = form.save(commit=False)
        if is_professor(request.user) and not is_admin_escola(request.user):
            novo.professor = professor_do_usuario(request.user)
        if not _pode_editar_monitoria(request.user, novo):
            return HttpResponseForbidden("Escola/professor fora do seu escopo.")
        novo.save()
        messages.success(request, "Monitoria atualizada.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/form.html", {"form": form, "titulo": "Editar Monitoria"})


@login_required
def monitoria_programacao_pdf(request):
    """PDF da programação das monitorias (mesma visão de /monitorias/),
    com cabeçalho e logo da escola."""
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

    monitorias = (
        Monitoria.objects.filter(ativo=True, escola__in=escolas_do_usuario(request.user))
        .select_related("escola", "professor", "materia", "dia")
    )
    dias = list(Dias.objects.all().order_by("ordem", "id"))

    # Agrupa por escola → (professor, materia) → {dia_id: [monitorias]}
    escolas_dict = {}
    escolas_obj = {}
    for m in monitorias:
        esc_key = (m.escola_id, m.escola.nome_escola if m.escola else "—")
        prof_key = (m.professor_id, m.professor.nome_professor, m.materia_id, m.materia.nome_materia)
        escolas_dict.setdefault(esc_key, {}).setdefault(prof_key, {}).setdefault(m.dia_id, []).append(m)
        if m.escola_id:
            escolas_obj[esc_key] = m.escola

    buf = BytesIO()
    PAGE_W = landscape(A4)[0]
    margem = 1.2 * cm
    largura_util = PAGE_W - 2 * margem
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=margem, rightMargin=margem,
        topMargin=margem, bottomMargin=margem,
        title="Programação das Monitorias",
    )
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10, alignment=1)
    cell_left = ParagraphStyle("cell_l", parent=styles["Normal"], fontSize=9, leading=11, alignment=0)
    head = ParagraphStyle("head", parent=styles["Normal"], fontSize=9, leading=11,
                          alignment=1, textColor=colors.white, fontName="Helvetica-Bold")

    story = []

    if not escolas_dict:
        story.append(Paragraph("Nenhuma monitoria cadastrada.", styles["Normal"]))

    escolas_ord = sorted(escolas_dict.items(), key=lambda x: x[0][1] or "")
    for i, ((esc_id, esc_nome), profs) in enumerate(escolas_ord):
        # Apenas dias com pelo menos 1 monitoria nesta escola
        dias_ids_usados = {d_id for por_dia in profs.values() for d_id in por_dia.keys()}
        dias_usados = [d for d in dias if d.id in dias_ids_usados]
        if not dias_usados:
            continue

        escola = escolas_obj.get((esc_id, esc_nome))
        subtitulos = [
            "Programação das <b>Monitorias</b>",
            f"Emitido em {date.today().strftime('%d/%m/%Y')}",
        ]
        story.append(cabecalho_pdf(escola, esc_nome or "Escola", subtitulos, largura_util))
        story.append(Spacer(1, 0.15 * cm))
        story.append(HRFlowable(width="100%", thickness=1.2,
                                color=colors.HexColor("#0d6efd"),
                                spaceBefore=0, spaceAfter=0.3 * cm))

        # Cabeçalho da tabela
        header_row = [
            Paragraph("DOCENTE", head),
            Paragraph("COMPONENTE<br/>CURRICULAR", head),
        ] + [Paragraph(d.dias.upper(), head) for d in dias_usados]
        rows = [header_row]

        for (prof_id, prof_nome, mat_id, mat_nome), por_dia in sorted(profs.items(), key=lambda x: x[0][1]):
            row = [
                Paragraph(f"<b>{prof_nome}</b>", cell_left),
                Paragraph(mat_nome or "—", cell_left),
            ]
            for d in dias_usados:
                items = por_dia.get(d.id, [])
                if not items:
                    row.append(Paragraph("<font color='#bbb'>—</font>", cell))
                else:
                    blocos = []
                    for m in items:
                        partes = [f"<b>{m.faixa_horaria}</b>"]
                        if m.nivel_ensino:
                            partes.append(f"<font size=7 color='#666'>{m.nivel_ensino}</font>")
                        partes.append(f"<font size=7>Sala {m.sala}</font>")
                        if m.observacao:
                            partes.append(f"<font size=7 color='#666'><i>{m.observacao}</i></font>")
                        blocos.append("<br/>".join(partes))
                    row.append(Paragraph("<br/><br/>".join(blocos), cell))
            rows.append(row)

        # Larguras: Docente, Componente + dias proporcionais
        col_doc = 4.5 * cm
        col_comp = 4.0 * cm
        restante = largura_util - col_doc - col_comp
        col_dia = restante / len(dias_usados)
        col_widths = [col_doc, col_comp] + [col_dia] * len(dias_usados)

        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfd")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.4 * cm))
        if i < len(escolas_ord) - 1:
            story.append(PageBreak())

    doc.build(story)
    pdf = buf.getvalue()
    buf.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = 'inline; filename="monitorias.pdf"'
    return resp


@professor_ou_admin_required
def monitoria_delete(request, pk):
    obj = get_object_or_404(Monitoria, pk=pk)
    if not _pode_editar_monitoria(request.user, obj):
        return HttpResponseForbidden("Sem permissão.")
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Monitoria excluída.")
        return redirect("cal:monitoria_list")
    return render(request, "diario/monitoria/confirm_delete.html", {"obj": obj, "titulo": "Excluir Monitoria"})
