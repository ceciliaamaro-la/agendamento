import logging
import traceback

from agenda.models import AgendaEvento
from agenda.utils.hash_evento import gerar_hash

logger = logging.getLogger(__name__)


def salvar_eventos(eventos, turma=None):

    salvos = 0
    ignorados = 0

    for evento in eventos:

        try:

            hash_evento = gerar_hash(evento)

            if AgendaEvento.objects.filter(hash=hash_evento).exists():
                ignorados += 1
                continue

            AgendaEvento.objects.create(
                turma=turma,
                data=evento["data"],
                dia=evento["dia"],
                titulo=evento["titulo"],
                tipo=evento["tipo"],
                datas=evento["datas"],
                descricao=evento["descricao"],
                hash=hash_evento,
            )

            salvos += 1

            logger.info(f"💾 Evento salvo: {evento['titulo']}")

        except Exception as e:
            logger.error(f"❌ Erro ao salvar evento '{evento.get('titulo', '?')}': {e}")
            traceback.print_exc()

    return {"salvos": salvos, "ignorados": ignorados}
