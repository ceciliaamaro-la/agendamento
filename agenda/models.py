from django.db import models

  
class Escola(models.Model):

    nome_escola = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nome_escola or "Escola"


class Turma(models.Model):

    escola = models.ForeignKey(
        Escola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    nome_turma = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nome_turma or "Turma"


class Aluno(models.Model):

    turma = models.ForeignKey(
        Turma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    nome_aluno = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    email = models.TextField(
        blank=True,
        null=True
    )

    senha = models.TextField(
        blank=True,
        null=True
    )
    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nome_aluno or "Aluno"

class ConexaoAgenda(models.Model):

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE,
        unique=True
    )

    login = models.CharField(max_length=100)

    senha = models.CharField(max_length=100)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.turma.nome_turma}"

class AgendaEvento(models.Model):

    turma = models.ForeignKey(
        Turma,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    data = models.DateField()

    dia = models.CharField(
        max_length=5
    )

    titulo = models.CharField(
        max_length=255
    )

    tipo = models.CharField(
        max_length=50
    )

    datas = models.CharField(
        max_length=100
    )

    descricao = models.TextField()

    hash = models.CharField(
        max_length=64,
        unique=True
    )

    enviado_whatsapp = models.BooleanField(
        default=False
    )

    criado_em = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"{self.data} - {self.titulo}"
    
class WhatsAppEnvio(models.Model):

    evento = models.ForeignKey(
        AgendaEvento,
        on_delete=models.CASCADE
    )

    numero_destino = models.CharField(
        max_length=20
    )

    hash_evento = models.CharField(
        max_length=64
    )

    enviado_em = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        default="enviado"
    )
    class Meta:
            unique_together = ("evento", "numero_destino", "hash_evento")
    def __str__(self):

        return f"{self.numero_destino} - {self.hash_evento}"