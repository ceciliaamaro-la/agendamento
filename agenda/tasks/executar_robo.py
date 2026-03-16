# # import os
# # import sys
# # import django

# # # caminho da raiz do projeto
# # BASE_DIR = os.path.abspath(
# #     os.path.join(os.path.dirname(__file__), "../../")
# # )

# # sys.path.append(BASE_DIR)

# # os.environ.setdefault(
# #     "DJANGO_SETTINGS_MODULE",
# #     "core.settings"
# # )

# # django.setup()

# # from agenda.robots.agenda_robot import extrair_eventos
# # from agenda.services.salvar_eventos_service import salvar_eventos
# # from agenda.services.envio_service import enviar_tarefas


# # def executar():

# #     print("🚀 Iniciando robô...")

# #     eventos = extrair_eventos()

# #     print("Eventos encontrados:", len(eventos))

# #     resultado = salvar_eventos(eventos)

# #     print("\nResultado:")

# #     print("Eventos salvos:", resultado["salvos"])

# #     print("Eventos ignorados:", resultado["ignorados"])

# #     print("\n📲 Enviando WhatsApp...")

# #     enviar_tarefas()

# #     print("Envio finalizado")


# # if __name__ == "__main__":

# #     executar()

# import os
# import django
# import sys

# # caminho da raiz do projeto
# BASE_DIR = os.path.abspath(
#     os.path.join(os.path.dirname(__file__), "../../")
# )

# sys.path.append(BASE_DIR)

# os.environ.setdefault(
#     "DJANGO_SETTINGS_MODULE",
#     "core.settings"
# )
# django.setup()

# # from agenda.services.sync_agenda import sincronizar_agendas
# # from agenda.services.envio_service import enviar_tarefas


# # print("🚀 Iniciando robô...")

# # sincronizar_agendas()

# # print("\n📲 Enviando WhatsApp...")

# # enviar_tarefas()

# # print("\n✅ Processo finalizado")


# # import os
# # import sys
# # import django

# # BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# # sys.path.append(BASE_DIR)

# # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dever.settings")
# # django.setup()

# from agenda.services.sync_agenda import sincronizar_agendas
# from agenda.services.envio_service import enviar_tarefas


# print("🚀 Iniciando robô...")

# # 1️⃣ Buscar eventos no site
# sincronizar_agendas()

# # 2️⃣ Enviar WhatsApp
# print("\n📲 Enviando WhatsApp...")
# enviar_tarefas()

# print("\n✅ Processo finalizado")


import os
import sys
import django
import logging
import traceback

# caminho da raiz do projeto
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../")
)

sys.path.append(BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "core.settings"
)

django.setup()

logger = logging.getLogger(__name__)

from agenda.services.sync_agenda import sincronizar_agendas
from agenda.services.envio_service import enviar_tarefas

logger.info("🚀 Iniciando robô...")

try:

    logger.info("🔎 Sincronizando agenda...")
    sincronizar_agendas()

    logger.info("📲 Enviando WhatsApp...")
    enviar_tarefas()

    logger.info("✅ Processo finalizado")

except Exception as e:

    logger.error("❌ ERRO NO ROBÔ")
    logger.error(str(e))
    traceback.print_exc()