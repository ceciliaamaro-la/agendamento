from .evolution_client import EvolutionAPIClient
from .models import MensagemWhatsApp


client = EvolutionAPIClient()


def enviar_whatsapp(instancia, numero, texto):

    response = client.enviar_texto(
        instancia.nome_instancia,
        numero,
        texto
    )

    message_id = None

    try:
        message_id = response["key"]["id"]
    except:
        pass

    msg = MensagemWhatsApp.objects.create(
        instance=instancia,
        numero_destino=numero,
        mensagem=texto,
        message_id=message_id
    )

    return msg