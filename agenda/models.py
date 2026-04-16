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

    # Campos legados (mantidos para compatibilidade com dados existentes)
    data = models.DateField(null=True, blank=True)
    dia = models.CharField(max_length=20, blank=True)
    datas = models.CharField(max_length=255, blank=True)

    # Campos principais
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=100, blank=True)

    # Datas estruturadas extraídas da visualização Lista
    inicio = models.DateTimeField(null=True, blank=True)
    termino = models.DateTimeField(null=True, blank=True)

    # Indica se o evento possui arquivo para download
    tem_anexo = models.BooleanField(default=False)

    # URL direta do anexo, capturada ao interceptar o clique no botão de download
    url_anexo = models.URLField(max_length=2048, blank=True, default="")

    hash = models.CharField(max_length=64, unique=True)

    enviado_whatsapp = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["data"]),
            models.Index(fields=["inicio"]),
            models.Index(fields=["turma"]),
        ]

    def __str__(self):
        dt = self.inicio or self.data
        if dt:
            return f"{self.titulo} — {dt.strftime('%d/%m/%Y') if hasattr(dt, 'strftime') else dt}"
        return self.titulo


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

    # Per-student visibility flag. False hides the task from the student's
    # list without affecting other students linked to the same event.
    visivel = models.BooleanField(default=True)

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
