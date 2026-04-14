from agenda.models import AgendaEvento
from agenda.utils.hash_evento import gerar_hash


def salvar_eventos(eventos, turma=None):

    objetos = []
    ignorados = 0

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
                data=evento["data"],
                dia=evento["dia"],
                titulo=evento["titulo"],
                tipo=evento["tipo"],
                datas=evento["datas"],
                descricao=evento["descricao"],
                hash=hash_evento,
            )
        )

    AgendaEvento.objects.bulk_create(objetos, ignore_conflicts=True)

    return {
        "salvos": len(objetos),
        "ignorados": ignorados
    }