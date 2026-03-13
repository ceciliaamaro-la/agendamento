from rest_framework import serializers
from .models import WhatsAppInstance, MensagemWhatsApp


class WhatsAppInstanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = WhatsAppInstance
        fields = "__all__"


class MensagemWhatsAppSerializer(serializers.ModelSerializer):

    class Meta:
        model = MensagemWhatsApp
        fields = "__all__"