from celery import shared_task
from agenda.services.sync_agenda import sincronizar_agenda


@shared_task
def task_sincronizar_agenda():
    sincronizar_agenda()