from agenda.models import AgendaEvento
from agenda.utils.hash_evento import gerar_hash


def salvar_eventos(eventos, turma=None):

    ignorados = 0
    objetos = []

    hashes_existentes = set(
        AgendaEvento.objects.values_list("hash", flat=True)
    )

    for evento in eventos:

        hash_evento = gerar_hash(evento)

        if hash_evento in hashes_existentes:
            ignorados += 1
            continue

        objetos.append(
            AgendaEvento(
                turma=turma,
                titulo=evento["titulo"],
                descricao=evento.get("descricao", ""),
                tipo=evento.get("tipo", ""),
                inicio=evento.get("inicio"),
                termino=evento.get("termino"),
                tem_anexo=evento.get("tem_anexo", False),
                url_anexo=evento.get("url_anexo", ""),
                # Legacy fields — populated when available for backward compat
                data=evento.get("data"),
                dia=evento.get("dia", ""),
                datas=evento.get("datas", ""),
                hash=hash_evento,
            )
        )

    AgendaEvento.objects.bulk_create(objetos, ignore_conflicts=True)

    return {
        "salvos": len(objetos),
        "ignorados": ignorados,
    }
