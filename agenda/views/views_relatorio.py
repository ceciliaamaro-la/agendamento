"""Relatório PDF: aulas, deveres e chamada do dia.

Endpoint: /diario/relatorio/?data=YYYY-MM-DD[&turma=<id>]

- Cabeçalho: logo da escola, nome do professor, matéria, escola, data
- Para cada aula do dia: conteúdo, dever, data de entrega + tabela de chamada
"""

import io
import os
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..models import DiarioAluno
from ..services.escopo import (
    aulas_do_usuario, professor_do_usuario, is_admin_escola,
)


# Paleta — alinhada ao views_pdf.py
AZUL = colors.HexColor("#0d6efd")
VERDE = colors.HexColor("#198754")
VERMELHO = colors.HexColor("#dc3545")
CINZA_CLARO = colors.HexColor("#f8f9fa")
CINZA_BORDA = colors.HexColor("#dee2e6")
CINZA_TEXTO = colors.HexColor("#6c757d")
BRANCO = colors.white
PRETO = colors.HexColor("#212529")


def _styles():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Normal"], fontSize=18,
                                 textColor=AZUL, fontName="Helvetica-Bold"),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=10,
                              textColor=CINZA_TEXTO, fontName="Helvetica"),
        "secao": ParagraphStyle("secao", parent=base["Normal"], fontSize=12,
                                textColor=BRANCO, fontName="Helvetica-Bold",
                                leftIndent=4),
        "label": ParagraphStyle("label", parent=base["Normal"], fontSize=8,
                                textColor=CINZA_TEXTO, fontName="Helvetica-Bold"),
        "valor": ParagraphStyle("valor", parent=base["Normal"], fontSize=10,
                                textColor=PRETO, fontName="Helvetica"),
        "txt": ParagraphStyle("txt", parent=base["Normal"], fontSize=9,
                              textColor=PRETO, leading=12),
        "rodape": ParagraphStyle("rodape", parent=base["Normal"], fontSize=7,
                                 textColor=CINZA_TEXTO, alignment=TA_CENTER),
        "vazio": ParagraphStyle("vazio", parent=base["Normal"], fontSize=9,
                                textColor=CINZA_TEXTO, alignment=TA_CENTER,
                                fontName="Helvetica-Oblique"),
    }


def _cabecalho_secao(texto, cor, largura):
    st = _styles()
    t = Table([[Paragraph(texto, st["secao"])]], colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _tabela_chamada(aula, largura):
    st = _styles()
    registros = (
        DiarioAluno.objects.filter(aula=aula)
        .select_related("aluno")
        .order_by("aluno__nome_aluno")
    )
    if not registros.exists():
        return Paragraph("Nenhum aluno registrado nesta aula.", st["vazio"])

    rows = [[
        Paragraph("<b>#</b>", st["label"]),
        Paragraph("<b>Aluno</b>", st["label"]),
        Paragraph("<b>Presença</b>", st["label"]),
        Paragraph("<b>Observação</b>", st["label"]),
    ]]
    presentes = ausentes = 0
    for i, r in enumerate(registros, start=1):
        if r.presente:
            presentes += 1
            marca = Paragraph('<font color="#198754"><b>P</b></font>', st["valor"])
        else:
            ausentes += 1
            marca = Paragraph('<font color="#dc3545"><b>F</b></font>', st["valor"])
        rows.append([
            Paragraph(str(i), st["txt"]),
            Paragraph(r.aluno.nome_aluno, st["txt"]),
            marca,
            Paragraph(r.observacao or "", st["txt"]),
        ])
    rows.append([
        "", Paragraph("<b>Totais</b>", st["label"]),
        Paragraph(f"<b>P:</b> {presentes}  <b>F:</b> {ausentes}", st["txt"]),
        "",
    ])

    col_widths = [0.9 * cm, 6.5 * cm, 2.0 * cm, largura - 9.4 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, -1), (-1, -1), CINZA_CLARO),
        ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
    ]
    # zebra
    for i in range(1, len(rows) - 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), CINZA_CLARO))
    t.setStyle(TableStyle(style))
    return t


def _bloco_aula(aula, largura):
    st = _styles()
    info = [
        [Paragraph("MATÉRIA", st["label"]),
         Paragraph(str(aula.materia or "—"), st["valor"]),
         Paragraph("TURMA", st["label"]),
         Paragraph(str(aula.turma or "—"), st["valor"])],
        [Paragraph("PROFESSOR(A)", st["label"]),
         Paragraph(str(aula.professor or "—"), st["valor"]),
         Paragraph("LIVRO", st["label"]),
         Paragraph(str(aula.livro or "—"), st["valor"])],
    ]
    info_tbl = Table(info, colWidths=[2.6 * cm, (largura / 2 - 2.6 * cm),
                                      2.0 * cm, (largura / 2 - 2.0 * cm)])
    info_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))

    blocos = [info_tbl, Spacer(1, 0.2 * cm)]

    conteudo = (aula.conteudo or "").strip()
    if conteudo:
        blocos.append(_cabecalho_secao("  Conteúdo ministrado", AZUL, largura))
        blocos.append(Spacer(1, 0.15 * cm))
        blocos.append(Paragraph(conteudo.replace("\n", "<br/>"), st["txt"]))
        blocos.append(Spacer(1, 0.25 * cm))

    dever = (aula.dever or "").strip()
    if dever:
        entrega = aula.data_entrega.strftime("%d/%m/%Y") if aula.data_entrega else "—"
        blocos.append(_cabecalho_secao(
            f"  Dever de casa  (entrega: {entrega})", VERMELHO, largura
        ))
        blocos.append(Spacer(1, 0.15 * cm))
        blocos.append(Paragraph(dever.replace("\n", "<br/>"), st["txt"]))
        blocos.append(Spacer(1, 0.25 * cm))

    obs = (aula.observacao or "").strip()
    if obs:
        blocos.append(_cabecalho_secao("  Observações", CINZA_TEXTO, largura))
        blocos.append(Spacer(1, 0.15 * cm))
        blocos.append(Paragraph(obs.replace("\n", "<br/>"), st["txt"]))
        blocos.append(Spacer(1, 0.25 * cm))

    blocos.append(_cabecalho_secao("  Chamada", VERDE, largura))
    blocos.append(Spacer(1, 0.15 * cm))
    blocos.append(_tabela_chamada(aula, largura))

    return KeepTogether(blocos)


def _cabecalho_documento(escola, professor, data_ref, largura):
    """Header com logo da escola + identificação do professor + data."""
    st = _styles()

    # Logo
    logo_flow = None
    if escola and getattr(escola, "logo", None) and escola.logo:
        try:
            logo_flow = Image(escola.logo.path, width=2.0 * cm, height=2.0 * cm,
                              kind="proportional")
        except Exception:
            logo_flow = None
    if logo_flow is None:
        # Fallback: usa o ícone padrão do app, se existir
        fallback = os.path.join(settings.BASE_DIR, "static", "img", "icon.png")
        if os.path.exists(fallback):
            logo_flow = Image(fallback, width=1.6 * cm, height=1.6 * cm)
        else:
            logo_flow = Spacer(1, 0.1 * cm)

    info = [
        Paragraph("Relatório de Aulas e Chamada", st["titulo"]),
        Paragraph(
            f"<b>Escola:</b> {escola.nome_escola if escola else '—'}",
            st["sub"],
        ),
        Paragraph(
            f"<b>Professor(a):</b> {professor.nome_professor if professor else '—'}"
            + (f"  ·  <b>Matéria:</b> {professor.materia}" if professor and professor.materia_id else ""),
            st["sub"],
        ),
        Paragraph(
            f"<b>Data:</b> {data_ref.strftime('%d/%m/%Y')}  "
            f"({['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][data_ref.weekday()]})",
            st["sub"],
        ),
    ]
    header_tbl = Table([[logo_flow, info]],
                       colWidths=[2.4 * cm, largura - 2.4 * cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return header_tbl


@login_required
def relatorio_diario_pdf(request):
    """Gera PDF com todas as aulas/deveres + chamada do dia para o usuário."""
    # Data de referência
    data_str = request.GET.get("data") or date.today().strftime("%Y-%m-%d")
    try:
        data_ref = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        data_ref = date.today()

    turma_id = request.GET.get("turma")

    # Aulas visíveis no escopo do usuário, no dia escolhido
    qs = aulas_do_usuario(request.user).filter(data_aula=data_ref).select_related(
        "escola", "turma", "professor", "materia", "livro"
    ).order_by("turma__nome_turma", "criado_em")
    if turma_id:
        qs = qs.filter(turma_id=turma_id)
    aulas = list(qs)

    # Identificação do cabeçalho
    professor = professor_do_usuario(request.user)
    if aulas:
        escola = aulas[0].escola
        if not professor and is_admin_escola(request.user):
            # admin: usa o professor da primeira aula como referência
            professor = aulas[0].professor
    else:
        escola = None

    # ── Monta PDF ──────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    margem = 1.6 * cm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=margem, rightMargin=margem,
        topMargin=margem, bottomMargin=margem,
        title=f"Relatório {data_ref.strftime('%d-%m-%Y')}",
        author="Agenda Escolar",
    )
    largura = A4[0] - 2 * margem
    st = _styles()
    story = [
        _cabecalho_documento(escola, professor, data_ref, largura),
        Spacer(1, 0.2 * cm),
        HRFlowable(width="100%", thickness=1.2, color=AZUL,
                   spaceBefore=0, spaceAfter=0.3 * cm),
    ]

    if not aulas:
        story.append(Paragraph(
            f"Nenhuma aula registrada em {data_ref.strftime('%d/%m/%Y')}.",
            st["vazio"],
        ))
    else:
        for i, aula in enumerate(aulas):
            story.append(_bloco_aula(aula, largura))
            if i < len(aulas) - 1:
                story.append(Spacer(1, 0.4 * cm))
                story.append(HRFlowable(
                    width="100%", thickness=0.4, color=CINZA_BORDA,
                    spaceBefore=0, spaceAfter=0.3 * cm,
                ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.4, color=CINZA_BORDA))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(
        f"Gerado em {date.today().strftime('%d/%m/%Y')} — Agenda Escolar",
        st["rodape"],
    ))

    doc.build(story)
    buffer.seek(0)
    nome = f"relatorio_{data_ref.strftime('%Y%m%d')}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{nome}"'
    return response
