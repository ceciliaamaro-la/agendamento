import time
import logging

from agenda.models import AgendaEvento, Aluno, WhatsAppEnvio
from evolution.app import enviar_texto

logger = logging.getLogger(__name__)


def enviar_tarefas():

    logger.info("📲 Iniciando envio WhatsApp")

    eventos = AgendaEvento.objects.filter(
        enviado_whatsapp=False
    )

    logger.info(f"Eventos pendentes: {eventos.count()}")

    for evento in eventos:

        turma = evento.turma

        alunos = Aluno.objects.filter(turma=turma)

        mensagem = f"""
📚 *Nova tarefa*

📌 {evento.titulo}
🗓 {evento.data}

{evento.descricao}
"""

        for aluno in alunos:

            numero = aluno.telefone

            # verifica se já enviou
            ja_enviado = WhatsAppEnvio.objects.filter(
                evento=evento,
                numero_destino=numero,
                hash_evento=evento.hash
            ).exists()

            if ja_enviado:

                logger.info(f"⚠ Já enviado para {numero}")
                continue

            try:

                response = enviar_texto(numero, mensagem)

                if response.status_code in [200, 201]:

                    WhatsAppEnvio.objects.create(
                        evento=evento,
                        numero_destino=numero,
                        hash_evento=evento.hash,
                        status="enviado"
                    )

                    logger.info(f"✅ Enviado para {numero}")

                    time.sleep(4)  # anti-bloqueio

            except Exception as e:

                logger.error(f"Erro envio {numero}: {e}")

        evento.enviado_whatsapp = True
        evento.save()

    logger.info("🚀 Envio finalizado")