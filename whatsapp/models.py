from django.db import models
from django.contrib.auth.models import User


class WhatsAppInstance(models.Model):

    STATUS_CHOICES = [
        ('creating', 'Criando'),
        ('qr_ready', 'QR pronto'),
        ('connected', 'Conectado'),
        ('disconnected', 'Desconectado'),
        ('error', 'Erro'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    nome_instancia = models.CharField(max_length=100, unique=True)

    numero_telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='creating'
    )

    qr_code = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome_instancia} - {self.status}"


class MensagemWhatsApp(models.Model):

    instance = models.ForeignKey(
        WhatsAppInstance,
        on_delete=models.CASCADE
    )

    numero_destino = models.CharField(max_length=20)

    mensagem = models.TextField()

    status = models.CharField(
        max_length=20,
        default="enviado"
    )

    message_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.instance.nome_instancia} -> {self.numero_destino}"


class RegistroEnvio(models.Model):

    celular = models.CharField(max_length=20)

    mensagem = models.TextField()

    sucesso = models.BooleanField(default=False)

    data_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.celular} - {self.data_envio}"