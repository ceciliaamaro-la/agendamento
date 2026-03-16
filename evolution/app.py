import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('AUTHENTICATION_API_KEY')
url_base = "http://127.0.0.1:8080"
instancia = "agenda"

headers = {
    "Content-Type": "application/json",
    "apikey": API_KEY
}


def enviar_texto(numero, texto):
    url = f"{url_base}/message/sendText/{instancia}"
    payload = {
        "number": numero,
        "textMessage": {"text": texto}
    }
    return requests.post(url, headers=headers, json=payload)


def enviar_imagem(numero, imagem_url, legenda):
    url = f"{url_base}/message/sendMedia/{instancia}"
    payload = {
        "number": numero,
        "mediaMessage": {
            "mediatype": "image",
            "media": imagem_url,
            "caption": legenda
        }
    }
    return requests.post(url, headers=headers, json=payload)


def enviar_audio(numero, audio_url):
    url = f"{url_base}/message/sendWhatsAppAudio/{instancia}"
    payload = {
        "number": numero,
        "audioMessage": {
            "audio": audio_url
        }
    }
    return requests.post(url, headers=headers, json=payload)


def verificar_status(message_id):
    url = f"{url_base}/message/statusMessage/{instancia}"
    payload = {"messageId": message_id}
    return requests.post(url, headers=headers, json=payload)
