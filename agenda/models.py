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


# ---------------------------------------------------------------------------
# Módulo Diário / Deveres (portado do meudever)
# ---------------------------------------------------------------------------

class Materia(models.Model):
    nome_materia = models.CharField(max_length=100, verbose_name="Matéria")

    class Meta:
        ordering = ["nome_materia"]
        verbose_name = "Matéria"
        verbose_name_plural = "Matérias"

    def __str__(self):
        return self.nome_materia


class Professor(models.Model):
    escola = models.ForeignKey(
        Escola, on_delete=models.CASCADE, related_name="professores"
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="professores"
    )
    nome_professor = models.CharField(max_length=100, verbose_name="Nome")

    class Meta:
        ordering = ["nome_professor"]
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def __str__(self):
        return self.nome_professor


class Livro(models.Model):
    escola = models.ForeignKey(
        Escola, on_delete=models.CASCADE, related_name="livros"
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="livros"
    )
    nome_livro = models.CharField(max_length=100, verbose_name="Nome do livro")

    class Meta:
        ordering = ["nome_livro"]
        verbose_name = "Livro"
        verbose_name_plural = "Livros"

    def __str__(self):
        return self.nome_livro


class Dias(models.Model):
    dias = models.CharField(max_length=20, verbose_name="Dia da semana")
    ordem = models.IntegerField(default=0, verbose_name="Ordem")

    class Meta:
        ordering = ["ordem"]
        verbose_name = "Dia"
        verbose_name_plural = "Dias"

    def __str__(self):
        return self.dias


class OrdemHorario(models.Model):
    ordem = models.CharField(max_length=20, verbose_name="Ordem do horário")

    class Meta:
        verbose_name = "Ordem de Horário"
        verbose_name_plural = "Ordens de Horário"

    def __str__(self):
        return self.ordem


class Horario(models.Model):
    escola = models.ForeignKey(
        Escola, on_delete=models.CASCADE, related_name="horarios"
    )
    turma = models.ForeignKey(
        Turma, on_delete=models.CASCADE, related_name="horarios"
    )
    dia = models.ForeignKey(
        Dias, on_delete=models.CASCADE, related_name="horarios"
    )
    ordem = models.ForeignKey(
        OrdemHorario, on_delete=models.CASCADE, related_name="horarios"
    )
    professor = models.ForeignKey(
        Professor, on_delete=models.CASCADE, related_name="horarios"
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="horarios"
    )

    class Meta:
        ordering = ["turma", "dia__ordem", "ordem"]
        verbose_name = "Horário"
        verbose_name_plural = "Horários"

    def __str__(self):
        return f"{self.turma} — {self.dia} — {self.ordem} — {self.materia}"


class Aula(models.Model):
    """Registro de aula: conteúdo ministrado, dever de casa e data de entrega."""

    escola = models.ForeignKey(
        Escola, on_delete=models.CASCADE, related_name="aulas"
    )
    turma = models.ForeignKey(
        Turma, on_delete=models.CASCADE, related_name="aulas"
    )
    professor = models.ForeignKey(
        Professor, on_delete=models.CASCADE, related_name="aulas"
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="aulas"
    )
    livro = models.ForeignKey(
        Livro, on_delete=models.SET_NULL, null=True, blank=True, related_name="aulas"
    )
    conteudo = models.TextField(verbose_name="Conteúdo ministrado", blank=True)
    data_aula = models.DateField(verbose_name="Data da aula", null=True, blank=True)
    dever = models.TextField(verbose_name="Dever de casa", blank=True)
    data_entrega = models.DateField(verbose_name="Data de entrega", null=True, blank=True)
    observacao = models.TextField(verbose_name="Observação geral", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_aula", "-criado_em"]
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"

    def dias_para_entrega(self):
        from datetime import date
        if self.data_entrega:
            return (self.data_entrega - date.today()).days
        return None

    def __str__(self):
        return f"{self.turma} — {self.materia} — {self.data_aula}"


class DiarioAluno(models.Model):
    aula = models.ForeignKey(
        Aula, on_delete=models.CASCADE, related_name="diario"
    )
    aluno = models.ForeignKey(
        Aluno, on_delete=models.CASCADE, related_name="diario"
    )
    presente = models.BooleanField(default=True, verbose_name="Presente")
    observacao = models.TextField(verbose_name="Observação individual", blank=True)

    class Meta:
        unique_together = ("aula", "aluno")
        verbose_name = "Registro do Diário"
        verbose_name_plural = "Registros do Diário"

    def __str__(self):
        return f"{'Presente' if self.presente else 'Falta'} — {self.aluno} — {self.aula}"


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
