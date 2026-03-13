import requests
import json
import os
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Configurações (agora lidas do .env)
API_KEY = os.getenv('AUTHENTICATION_API_KEY')
url_base = "http://127.0.0.1:8080"
instancia = "agenda"


headers = {
    "Content-Type": "application/json",
    "apikey": API_KEY
}

# 1. Enviar texto simples
def enviar_texto(numero, texto):
    url = f"{url_base}/message/sendText/{instancia}"
    payload = {
        "number": numero,
        "textMessage": {"text": texto}
    }
    return requests.post(url, headers=headers, json=payload)

# 2. Enviar imagem
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

# 3. Enviar áudio
def enviar_audio(numero, audio_url):
    url = f"{url_base}/message/sendWhatsAppAudio/{instancia}"
    payload = {
        "number": numero,
        "audioMessage": {
            "audio": audio_url
        }
    }
    return requests.post(url, headers=headers, json=payload)

# 4. Verificar status da mensagem
def verificar_status(message_id):
    url = f"{url_base}/message/statusMessage/{instancia}"
    payload = {"messageId": message_id}
    return requests.post(url, headers=headers, json=payload)

# Teste
response = enviar_texto("5561985731668", "Teste2!")
if response.status_code == 201:
    message_id = response.json()['key']['id']
    print(f"Mensagem enviada! ID: {message_id}")