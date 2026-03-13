from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import WhatsAppInstance
from .serializers import WhatsAppInstanceSerializer
from .evolution_client import EvolutionAPIClient


client = EvolutionAPIClient()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def criar_instancia(request):

    nome = request.data.get("nome_instancia")

    instancia = WhatsAppInstance.objects.create(
        user=request.user,
        nome_instancia=nome
    )

    client.criar_instancia(nome)

    qr = client.obter_qrcode(nome)

    instancia.qr_code = qr.get("qrcode", {}).get("base64")

    instancia.status = "qr_ready"

    instancia.save()

    serializer = WhatsAppInstanceSerializer(instancia)

    return Response(serializer.data)