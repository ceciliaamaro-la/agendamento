import requests
from django.conf import settings


class EvolutionAPIClient:

    def __init__(self):

        self.base_url = settings.EVOLUTION_API["BASE_URL"]

        self.headers = {
            "Content-Type": "application/json",
            "apikey": settings.EVOLUTION_API["API_KEY"]
        }

    def criar_instancia(self, instance):

        url = f"{self.base_url}/instance/create"

        payload = {
            "instanceName": instance,
            "qrcode": True
        }

        r = requests.post(url, json=payload, headers=self.headers)

        return r.json()

    def obter_qrcode(self, instance):

        url = f"{self.base_url}/instance/connect/{instance}"

        r = requests.get(url, headers=self.headers)

        return r.json()

    def enviar_texto(self, instance, numero, texto):

        url = f"{self.base_url}/message/sendText/{instance}"

        payload = {
            "number": numero,
            "textMessage": {
                "text": texto
            }
        }

        r = requests.post(url, json=payload, headers=self.headers)

        return r.json()

    def verificar_conexao(self, instance):

        url = f"{self.base_url}/instance/connectionState/{instance}"

        r = requests.get(url, headers=self.headers)

        return r.json()