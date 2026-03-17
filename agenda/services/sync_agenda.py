import logging
import traceback

from agenda.agenda_robot import extrair_eventos
from agenda.services.salvar_eventos_service import salvar_eventos
# from agenda.services.envio_service import enviar_tarefas  # ⏸ WhatsApp desativado temporariamente
from agenda.models import ConexaoAgenda

logger = logging.getLogger(__name__)


def sincronizar_agenda():

    logger.info("🚀 Iniciando sincronização da agenda")

    try:

        conexoes = ConexaoAgenda.objects.filter(ativo=True)

        logger.info(f"🔎 Buscando conexões: {conexoes.count()} encontradas")

        if not conexoes.exists():
            logger.info("📭 Nenhuma conexão ativa encontrada")
            return

        for conexao in conexoes:

            logger.info(f"🏫 Processando turma: {conexao.turma}")

            eventos = extrair_eventos(conexao.login, conexao.senha)

            logger.info(f"📅 Eventos encontrados: {len(eventos)}")

            resultado = salvar_eventos(eventos, turma=conexao.turma)

            logger.info(
                f"💾 Eventos salvos: {resultado['salvos']} | "
                f"Ignorados (já existentes): {resultado['ignorados']}"
            )

        # ⏸ Envio WhatsApp desativado temporariamente
        # if conexoes.exists():
        #     logger.info("📤 Enviando mensagens WhatsApp")
        #     enviar_tarefas()

    except Exception as e:

        logger.error("❌ ERRO NA SINCRONIZAÇÃO DA AGENDA")
        traceback.print_exc()


def sincronizar_agenda_com_resultado():
    """Igual a sincronizar_agenda(), mas retorna dict com totais para o painel."""
    logger.info("🚀 Iniciando sincronização (com resultado)")
    total = {'salvos': 0, 'ignorados': 0, 'conexoes': 0}
    try:
        conexoes = ConexaoAgenda.objects.filter(ativo=True)
        logger.info(f"🔎 Conexões ativas: {conexoes.count()}")
        for conexao in conexoes:
            logger.info(f"🏫 Processando turma: {conexao.turma}")
            eventos = extrair_eventos(conexao.login, conexao.senha)
            logger.info(f"📅 Eventos encontrados: {len(eventos)}")
            resultado = salvar_eventos(eventos, turma=conexao.turma)
            total['salvos']    += resultado['salvos']
            total['ignorados'] += resultado['ignorados']
            total['conexoes']  += 1
            logger.info(f"💾 Salvos: {resultado['salvos']} | Ignorados: {resultado['ignorados']}")
    except Exception as e:
        logger.error("❌ ERRO NA SINCRONIZAÇÃO DA AGENDA")
        traceback.print_exc()
        raise
    return total
