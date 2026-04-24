"""Utilitários compartilhados para geração de PDFs.

- `logo_para_escola(escola)` retorna o caminho da logo da escola
  (ou o ícone padrão do app como fallback).
- `cabecalho_pdf(escola, titulo, subtitulos, largura)` devolve uma Table
  pronta com a logo + título + linhas de subtítulo.
"""

import os
from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle


_AZUL = colors.HexColor("#0d6efd")
_CINZA = colors.HexColor("#6c757d")


def logo_para_escola(escola):
    """Retorna o caminho de uma imagem para usar como logo:
    1) escola.logo (upload do usuário) se existir;
    2) fallback: static/img/icon.png;
    3) None se nenhuma estiver disponível.
    """
    if escola is not None:
        logo = getattr(escola, "logo", None)
        if logo:
            try:
                if os.path.exists(logo.path):
                    return logo.path
            except (ValueError, AttributeError):
                pass
    fallback = os.path.join(settings.BASE_DIR, "static", "img", "icon.png")
    return fallback if os.path.exists(fallback) else None


def cabecalho_pdf(escola, titulo, subtitulos, largura, logo_size_cm=1.8):
    """Monta um Table de cabeçalho (logo + título + subtítulos).

    `subtitulos` é uma lista de strings (HTML simples permitido)."""
    base = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "pdf_titulo", parent=base["Normal"], fontSize=18,
        textColor=_AZUL, fontName="Helvetica-Bold", spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "pdf_sub", parent=base["Normal"], fontSize=10,
        textColor=_CINZA, fontName="Helvetica", spaceAfter=0,
    )

    bloco_texto = [Paragraph(titulo, titulo_style)]
    for s in subtitulos:
        if s:
            bloco_texto.append(Paragraph(s, sub_style))

    logo_path = logo_para_escola(escola)
    if logo_path:
        logo_flow = Image(
            logo_path,
            width=logo_size_cm * cm,
            height=logo_size_cm * cm,
            kind="proportional",
        )
        col_logo = (logo_size_cm + 0.4) * cm
        tbl = Table(
            [[logo_flow, bloco_texto]],
            colWidths=[col_logo, largura - col_logo],
        )
    else:
        tbl = Table([[bloco_texto]], colWidths=[largura])

    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl
