"""Agrupamento de itens (aulas, eventos, etc.) por escola → turma → matéria,
com ordenação híbrida das matérias:
  1) Primeiro, matérias com aula no dia atual, na ordem da grade;
  2) Depois, as demais em ordem alfabética.
"""

from collections import OrderedDict, defaultdict
from datetime import date

from ..models import Horario


def dia_ordem_hoje(quando=None):
    """Retorna o ``Dias.ordem`` correspondente ao dia (default = hoje).

    No banco: 1=Domingo, 2=Segunda, …, 7=Sábado.
    Python ``isoweekday``: 1=Segunda, …, 7=Domingo.
    """
    d = quando or date.today()
    return (d.isoweekday() % 7) + 1


def horarios_do_dia_por_turma(turma_ids, quando=None):
    """Para cada turma_id, retorna ``dict[materia_id] = posicao`` na grade do dia."""
    turma_ids = list(turma_ids)
    if not turma_ids:
        return {}
    ord_dia = dia_ordem_hoje(quando)
    qs = (
        Horario.objects
        .filter(turma_id__in=turma_ids, dia__ordem=ord_dia, materia__isnull=False)
        .select_related("ordem")
        .order_by("turma_id", "ordem__posicao", "ordem__id")
    )
    out = defaultdict(OrderedDict)
    for h in qs:
        d = out[h.turma_id]
        if h.materia_id not in d:
            d[h.materia_id] = len(d)
    return {tid: dict(d) for tid, d in out.items()}


def _chave_materia(materia, prio):
    nome = (getattr(materia, "nome_materia", "") or "").lower()
    if materia is None:
        return (1, 0, nome)
    pos = prio.get(materia.id)
    if pos is not None:
        return (0, pos, nome)
    return (1, 0, nome)


def estruturar(triples, *, sem_materia_label="Geral", sem_materia_icon="calendar-event"):
    """Recebe iterável de tuplas ``(escola_nome, turma_obj, materia_obj, item)``
    e devolve a estrutura usada nos templates::

        [
          {
            "nome": "Escola X",
            "turmas": [
              {
                "key": <turma_id>, "turma": <Turma>, "nome": "181M", "total": N,
                "tabs": [
                  {"id": "t1-mGERAL", "label": "...", "icon": "...", "items": [...]},
                  {"id": "t1-m42",     "label": "Matemática", "icon": "book", "items": [...]},
                  ...
                ]
              }
            ]
          }
        ]
    """
    agrup = OrderedDict()
    turma_ids = set()
    for esc_nome, turma, materia, it in triples:
        esc_nome = esc_nome or "—"
        agrup.setdefault(esc_nome, OrderedDict())
        tkey = turma.id if turma else "_sem"
        if tkey not in agrup[esc_nome]:
            agrup[esc_nome][tkey] = {
                "turma": turma,
                "materias": OrderedDict(),
                "sem": [],
            }
        if materia is not None:
            mats = agrup[esc_nome][tkey]["materias"]
            if materia.id not in mats:
                mats[materia.id] = {"materia": materia, "items": []}
            mats[materia.id]["items"].append(it)
        else:
            agrup[esc_nome][tkey]["sem"].append(it)
        if turma:
            turma_ids.add(turma.id)

    prio_por_turma = horarios_do_dia_por_turma(turma_ids)

    out = []
    for esc_nome, turmas in agrup.items():
        turmas_lista = []
        for tkey, dados in turmas.items():
            turma = dados["turma"]
            prio = prio_por_turma.get(turma.id, {}) if turma else {}

            mats = list(dados["materias"].values())
            mats.sort(key=lambda x: _chave_materia(x["materia"], prio))

            tabs = []
            if dados["sem"]:
                tabs.append({
                    "id": f"t{tkey}-mGERAL",
                    "label": sem_materia_label,
                    "icon": sem_materia_icon,
                    "items": dados["sem"],
                })
            for m in mats:
                tabs.append({
                    "id": f"t{tkey}-m{m['materia'].id}",
                    "label": m["materia"].nome_materia,
                    "icon": "book",
                    "items": m["items"],
                })
            total = sum(len(t["items"]) for t in tabs)
            turmas_lista.append({
                "key": tkey,
                "turma": turma,
                "nome": turma.nome_turma if turma else "Sem turma",
                "tabs": tabs,
                "total": total,
            })
        out.append({"nome": esc_nome, "turmas": turmas_lista})
    return out
