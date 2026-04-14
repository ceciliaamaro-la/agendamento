from django.db import models
from django.contrib.auth.models import User


class Escola(models.Model):

    nome_escola = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)

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

    criado_em = models.DateTimeField(auto_now_add=True)

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

    usuarios = models.ManyToManyField(
        User,
        blank=True,
        related_name='alunos',
        verbose_name='Usuários vinculados'
    )

    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Telefone (WhatsApp)',
        help_text='Número com DDI e DDD, ex: 5511999999999'
    )

    criado_em = models.DateTimeField(auto_now_add=True)

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

    ativo = models.BooleanField(default=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.turma.nome_turma}"


class AgendaEvento(models.Model):

    turma = models.ForeignKey("Turma", on_delete=models.CASCADE, null=True)

    data = models.DateField()
    dia = models.CharField(max_length=20, blank=True)
    titulo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=100, blank=True)
    datas = models.CharField(max_length=255, blank=True)
    descricao = models.TextField(blank=True)

    hash = models.CharField(max_length=64, unique=True)  # 🔥 ESSENCIAL

    enviado_whatsapp = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["data"]),
            models.Index(fields=["turma"]),
        ]


class TarefaCompleta(models.Model):

    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.CASCADE
    )

    evento = models.ForeignKey(
        AgendaEvento,
        on_delete=models.CASCADE
    )

    concluida = models.BooleanField(default=False)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("aluno", "evento")

    def __str__(self):
        status = "✅" if self.concluida else "⬜"
        return f"{status} {self.aluno} — {self.evento.titulo}"


class WhatsAppEnvio(models.Model):

    turma = models.ForeignKey(
        Turma,
        on_delete=models.CASCADE
    )

    hash_evento = models.CharField(max_length=64)

    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("turma", "hash_evento")

    def __str__(self):
        return f"Turma {self.turma} - {self.hash_evento[:12]}..."
