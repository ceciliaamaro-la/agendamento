import os
import sys
import django
import logging

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../")
)

sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

from agenda.services.sync_agenda import sincronizar_agenda

if __name__ == "__main__":

    logger.info("🚀 Iniciando robô")

    sincronizar_agenda()

    logger.info("✅ Processo finalizado")


