"""Sincroniza uma Aula com seu AgendaEvento espelho.

Quando uma Aula é criada ou atualizada em /aulas/nova/, espelhamos o registro
em AgendaEvento (tipo='Tarefa') para que apareça no calendário e nos fluxos
de WhatsApp. O vínculo é via OneToOneField AgendaEvento.aula → Aula.
"""

import hashlib
from datetime import datetime, time

from django.utils import timezone

from ..models import AgendaEvento


def _hash_para_aula(aula) -> str:
    base = f"aula-{aula.pk}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _to_dt(d):
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    return timezone.make_aware(datetime.combine(d, time(0, 0)))


def sincronizar_evento_da_aula(aula) -> AgendaEvento:
    """Cria/atualiza o AgendaEvento espelho da Aula informada."""
    materia_nome = aula.materia.nome_materia if aula.materia_id else "Aula"
    titulo = f"{materia_nome} — {aula.turma.nome_turma}" if aula.turma_id else materia_nome

    descricao_partes = []
    if aula.dever:
        descricao_partes.append(f"Dever: {aula.dever}")
    if aula.observacao:
        descricao_partes.append(f"Obs.: {aula.observacao}")
    descricao = "\n\n".join(descricao_partes)

    defaults = {
        "turma": aula.turma,
        "escola": aula.escola,
        "professor": aula.professor,
        "materia": aula.materia,
        "livro": aula.livro,
        "titulo": titulo,
        "tipo": "Tarefa",
        "descricao": descricao,
        "conteudo": aula.conteudo or "",
        "dever": aula.dever or "",
        "observacao": aula.observacao or "",
        "inicio": _to_dt(aula.data_aula),
        "termino": _to_dt(aula.data_entrega),
        "data": aula.data_entrega or aula.data_aula,
        "data_entrega": aula.data_entrega,
    }

    evento, created = AgendaEvento.objects.update_or_create(
        aula=aula,
        defaults={**defaults, "hash": _hash_para_aula(aula)},
    )
    return evento
