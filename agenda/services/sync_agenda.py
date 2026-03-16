import logging
import traceback

from agenda.agenda_robot import extrair_eventos
from agenda.services.envio_service import enviar_mensagem
from agenda.models import ConexaoAgenda, EventoAgenda

logger = logging.getLogger(__name__)


def sincronizar_agenda():

    logger.info("🚀 Iniciando robô...")

    try:

        logger.info("🔎 Buscando conexões de agenda")

        conexoes = ConexaoAgenda.objects.filter(ativo=True)

        logger.info(f"Total conexões: {conexoes.count()}")

        for conexao in conexoes:

            logger.info(f"🏫 Processando turma: {conexao.turma}")

            ultimo_evento = EventoAgenda.objects.filter(
                conexao=conexao
            ).order_by("-data_criacao").first()

            if ultimo_evento:
                logger.info(f"Último evento criado em: {ultimo_evento.data_criacao}")

            # -------------------------------------
            # EXECUTA O ROBÔ
            # -------------------------------------

            eventos = extrair_eventos(
                conexao.login,
                conexao.senha
            )

            logger.info(f"Eventos encontrados: {len(eventos)}")

            novos_eventos = []

            for evento in eventos:

                existe = EventoAgenda.objects.filter(
                    titulo=evento["titulo"],
                    data=evento["data"],
                    conexao=conexao
                ).exists()

                if not existe:

                    novo = EventoAgenda.objects.create(
                        conexao=conexao,
                        titulo=evento["titulo"],
                        tipo=evento["tipo"],
                        data=evento["data"],
                        descricao=evento["descricao"]
                    )

                    novos_eventos.append(novo)

            logger.info(f"Novos eventos: {len(novos_eventos)}")

            # -------------------------------------
            # ENVIO DE MENSAGEM (SOMENTE DEPOIS)
            # -------------------------------------

            if novos_eventos:

                logger.info("📤 Enviando mensagem")

                enviar_mensagem(novos_eventos)

                logger.info("✅ Mensagem enviada")

            else:

                logger.info("📭 Nenhum evento novo")

    except Exception as e:

        logger.error("❌ ERRO NO ROBÔ")
        logger.error(str(e))
        traceback.print_exc()