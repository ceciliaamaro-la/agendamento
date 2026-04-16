import io
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

BRASILIA = ZoneInfo("America/Sao_Paulo")

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models import Aluno, AgendaEvento, TarefaCompleta

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL       = colors.HexColor("#0d6efd")
VERDE      = colors.HexColor("#198754")
VERMELHO   = colors.HexColor("#dc3545")
AMARELO    = colors.HexColor("#ffc107")
CINZA_CLARO = colors.HexColor("#f8f9fa")
CINZA_BORDA = colors.HexColor("#dee2e6")
CINZA_TEXTO = colors.HexColor("#6c757d")
BRANCO     = colors.white
PRETO      = colors.HexColor("#212529")

# Cor por tipo de evento
_TIPO_COR = {
    "prova":     VERMELHO,
    "atividade": AZUL,
    "tarefa":    colors.HexColor("#fd7e14"),
    "lição":     colors.HexColor("#6f42c1"),
    "licao":     colors.HexColor("#6f42c1"),
}


def _cor_tipo(tipo: str) -> colors.Color:
    return _TIPO_COR.get(tipo.lower().strip(), CINZA_TEXTO)


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Normal"],
            fontSize=20,
            textColor=AZUL,
            fontName="Helvetica-Bold",
            spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            parent=base["Normal"],
            fontSize=11,
            textColor=CINZA_TEXTO,
            fontName="Helvetica",
            spaceAfter=0,
        ),
        "secao": ParagraphStyle(
            "secao",
            parent=base["Normal"],
            fontSize=12,
            textColor=BRANCO,
            fontName="Helvetica-Bold",
            leftIndent=6,
        ),
        "celula_titulo": ParagraphStyle(
            "celula_titulo",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=PRETO,
            leading=13,
        ),
        "celula_desc": ParagraphStyle(
            "celula_desc",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica",
            textColor=CINZA_TEXTO,
            leading=11,
        ),
        "celula_tipo": ParagraphStyle(
            "celula_tipo",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "celula_data": ParagraphStyle(
            "celula_data",
            parent=base["Normal"],
            fontSize=8,
            fontName="Helvetica",
            textColor=CINZA_TEXTO,
            alignment=TA_CENTER,
        ),
        "rodape": ParagraphStyle(
            "rodape",
            parent=base["Normal"],
            fontSize=7,
            textColor=CINZA_TEXTO,
            alignment=TA_CENTER,
        ),
        "vazio": ParagraphStyle(
            "vazio",
            parent=base["Normal"],
            fontSize=9,
            textColor=CINZA_TEXTO,
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=4,
        ),
    }


def _cabecalho_secao(texto: str, cor: colors.Color, largura: float):
    """Retorna uma Table de uma linha que funciona como cabeçalho colorido."""
    st = _estilos()
    t = Table([[Paragraph(texto, st["secao"])]], colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


def _tabela_eventos(eventos, concluidos_ids: set, largura: float):
    """Monta a tabela de eventos. Retorna None se lista vazia."""
    st = _estilos()

    if not eventos:
        return None

    # Cabeçalho da tabela
    header = [
        Paragraph("<b>Data</b>", st["celula_data"]),
        Paragraph("<b>Tipo</b>",  st["celula_tipo"]),
        Paragraph("<b>Tarefa / Descrição</b>", st["celula_titulo"]),
    ]

    rows = [header]
    row_colors = []  # (linha, cor_fundo)

    for i, evento in enumerate(eventos, start=1):
        concluida = evento.id in concluidos_ids
        cor_fundo = colors.HexColor("#e8f5e9") if concluida else BRANCO
        if i % 2 == 0 and not concluida:
            cor_fundo = CINZA_CLARO

        row_colors.append(("BACKGROUND", (0, i), (-1, i), cor_fundo))

        # Use inicio when available (timezone-aware); fall back to legacy data field.
        data_ref = evento.inicio.astimezone(BRASILIA).date() if evento.inicio else evento.data
        data_str = data_ref.strftime("%d/%m/%Y") if data_ref else "—"
        if data_ref == date.today():
            data_str += "\n(Hoje)"

        cor_tipo = _cor_tipo(evento.tipo)
        tipo_para = Paragraph(
            f'<font color="#{cor_tipo.hexval()[2:]}"><b>{evento.tipo}</b></font>',
            st["celula_tipo"],
        )

        titulo_texto = evento.titulo
        if concluida:
            titulo_texto = f'<strike>{titulo_texto}</strike>'

        conteudo = Paragraph(titulo_texto, st["celula_titulo"])
        if evento.descricao and evento.descricao.strip():
            desc = evento.descricao.strip()[:200]
            if len(evento.descricao.strip()) > 200:
                desc += "…"
            conteudo = [
                Paragraph(titulo_texto, st["celula_titulo"]),
                Paragraph(desc, st["celula_desc"]),
            ]
            # Empilha em célula usando lista de parágrafos
            from reportlab.platypus import KeepTogether
            conteudo = KeepTogether(conteudo) if not isinstance(conteudo, list) else conteudo

        rows.append([
            Paragraph(data_str, st["celula_data"]),
            tipo_para,
            conteudo if not isinstance(conteudo, list) else conteudo[0],
        ])

        # Se tem descrição, adiciona linha extra
        if isinstance(conteudo, list):
            rows[-1][2] = conteudo[0]
            # Adiciona descrição como sub-linha mesclada
            rows.append(["", "", conteudo[1]])
            row_colors.append(("BACKGROUND", (0, len(rows) - 1), (-1, len(rows) - 1), cor_fundo))
            row_colors.append(("SPAN", (0, len(rows) - 1), (1, len(rows) - 1)))

    col_widths = [2.2 * cm, 2.5 * cm, largura - 4.7 * cm]

    t = Table(rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Cabeçalho
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), BRANCO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Corpo
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (0, 1), (1, -1),  "CENTER"),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        # Grade
        ("GRID",          (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("LINEBELOW",     (0, 0), (-1, 0),  1,   AZUL),
    ]
    style_cmds.extend(row_colors)

    t.setStyle(TableStyle(style_cmds))
    return t


@login_required
def gerar_pdf_tarefas(request):
    """
    Gera um PDF com as tarefas do aluno (pendentes + concluídas)
    para a janela de datas padrão: ontem até +7 dias.
    """
    alunos_do_usuario = Aluno.objects.filter(
        usuarios=request.user
    ).select_related("turma").order_by("nome_aluno")

    aluno_id = request.GET.get("aluno_id")
    if aluno_id:
        aluno = get_object_or_404(alunos_do_usuario, pk=aluno_id)
    else:
        aluno = alunos_do_usuario.first()

    if not aluno:
        return HttpResponse("Nenhum aluno vinculado.", status=404)

    hoje = date.today()
    primeiro_mes_atual    = hoje.replace(day=1)
    primeiro_mes_anterior = (primeiro_mes_atual - timedelta(days=1)).replace(day=1)
    ultimo_mes_atual      = (primeiro_mes_atual + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    data_inicio = primeiro_mes_anterior
    data_fim    = ultimo_mes_atual + timedelta(days=10)

    # inicio is stored as UTC-aware; convert window boundaries accordingly.
    inicio_utc = datetime(data_inicio.year, data_inicio.month, data_inicio.day,
                          tzinfo=BRASILIA)
    fim_utc    = datetime(data_fim.year, data_fim.month, data_fim.day,
                          23, 59, 59, tzinfo=BRASILIA)

    eventos = (
        AgendaEvento.objects
        .filter(turma=aluno.turma)
        .filter(
            Q(inicio__gte=inicio_utc, inicio__lte=fim_utc) |
            Q(inicio__isnull=True, data__gte=data_inicio, data__lte=data_fim)
        )
        .order_by("inicio", "data")
    )

    concluidos_ids = set(
        TarefaCompleta.objects
        .filter(aluno=aluno, concluida=True)
        .values_list("evento_id", flat=True)
    )

    pendentes  = [e for e in eventos if e.id not in concluidos_ids]
    concluidas = [e for e in eventos if e.id in concluidos_ids]

    # ── Montar PDF ────────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    margem = 1.8 * cm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margem,
        rightMargin=margem,
        topMargin=margem,
        bottomMargin=margem,
        title=f"Tarefas — {aluno.nome_aluno}",
        author="Agenda Escolar",
    )

    largura_util = A4[0] - 2 * margem
    st = _estilos()
    story = []

    # ── Cabeçalho do documento ────────────────────────────────────────────────
    logo_path = os.path.join(settings.BASE_DIR, "static", "img", "icon.png")
    header_data = []
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.4 * cm, height=1.4 * cm)
        header_data = [[
            logo,
            [
                Paragraph("Agenda Escolar", st["titulo"]),
                Paragraph(
                    f"Tarefas de <b>{aluno.nome_aluno}</b>"
                    + (f" — {aluno.turma}" if aluno.turma else ""),
                    st["subtitulo"],
                ),
                Paragraph(
                    f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                    st["subtitulo"],
                ),
            ],
        ]]
        header_table = Table(header_data, colWidths=[1.8 * cm, largura_util - 1.8 * cm])
        header_table.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph("Agenda Escolar", st["titulo"]))
        story.append(Paragraph(
            f"Tarefas de <b>{aluno.nome_aluno}</b>"
            + (f" — {aluno.turma}" if aluno.turma else ""),
            st["subtitulo"],
        ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=AZUL, spaceAfter=0.4 * cm))

    # ── Seção Pendentes ───────────────────────────────────────────────────────
    story.append(_cabecalho_secao(
        f"  Pendentes ({len(pendentes)})", VERMELHO, largura_util
    ))
    story.append(Spacer(1, 0.2 * cm))

    tabela_pend = _tabela_eventos(pendentes, concluidos_ids, largura_util)
    if tabela_pend:
        story.append(tabela_pend)
    else:
        story.append(Paragraph("Nenhuma tarefa pendente neste período.", st["vazio"]))

    story.append(Spacer(1, 0.5 * cm))

    # ── Seção Concluídas ──────────────────────────────────────────────────────
    story.append(_cabecalho_secao(
        f"  Concluídas ({len(concluidas)})", VERDE, largura_util
    ))
    story.append(Spacer(1, 0.2 * cm))

    tabela_conc = _tabela_eventos(concluidas, concluidos_ids, largura_util)
    if tabela_conc:
        story.append(tabela_conc)
    else:
        story.append(Paragraph("Nenhuma tarefa concluída neste período.", st["vazio"]))

    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(
        f"Gerado em {hoje.strftime('%d/%m/%Y')} — Agenda Escolar",
        st["rodape"],
    ))

    doc.build(story)
    buffer.seek(0)

    nome_arquivo = f"tarefas_{aluno.nome_aluno.replace(' ', '_')}_{hoje.strftime('%Y%m%d')}.pdf"
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    return response
