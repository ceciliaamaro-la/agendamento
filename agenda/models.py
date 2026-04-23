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

    TURNO_MATUTINO = "M"
    TURNO_VESPERTINO = "V"
    TURNO_NOTURNO = "N"
    TURNO_INTEGRAL = "I"
    TURNO_CHOICES = [
        (TURNO_MATUTINO, "Matutino"),
        (TURNO_VESPERTINO, "Vespertino"),
        (TURNO_NOTURNO, "Noturno"),
        (TURNO_INTEGRAL, "Integral"),
    ]

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

    turno = models.CharField(
        max_length=1,
        choices=TURNO_CHOICES,
        blank=True,
        default="",
        verbose_name="Turno",
        help_text="Período em que a turma estuda.",
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_turma or "Turma"

    def get_turno_display_safe(self):
        return self.get_turno_display() if self.turno else ""


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

    turma = models.OneToOneField(
        Turma,
        on_delete=models.CASCADE,
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

    # ── Campos pedagógicos (opcionais) — unificação com /aulas/nova/ ──
    escola = models.ForeignKey(
        "Escola", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eventos",
    )
    professor = models.ForeignKey(
        "Professor", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eventos",
    )
    materia = models.ForeignKey(
        "Materia", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eventos",
    )
    livro = models.ForeignKey(
        "Livro", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="eventos",
    )
    conteudo = models.TextField(blank=True, verbose_name="Conteúdo ministrado")
    dever = models.TextField(blank=True, verbose_name="Dever de casa")
    data_entrega = models.DateField(null=True, blank=True, verbose_name="Data de entrega")
    observacao = models.TextField(blank=True, verbose_name="Observação geral")

    # Espelho da Aula registrada em /aulas/nova/ (quando o evento foi gerado pelo diário)
    aula = models.OneToOneField(
        "Aula", on_delete=models.CASCADE, null=True, blank=True,
        related_name="evento_espelho",
    )

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
    TURNO_CHOICES = [
        ("M", "Matutino"),
        ("V", "Vespertino"),
        ("N", "Noturno"),
        ("I", "Integral"),
    ]

    ordem = models.CharField(max_length=20, verbose_name="Ordem do horário")
    posicao = models.PositiveIntegerField(default=0, verbose_name="Posição")
    inicio = models.TimeField(null=True, blank=True, verbose_name="Início")
    termino = models.TimeField(null=True, blank=True, verbose_name="Término")
    turno = models.CharField(
        max_length=1,
        choices=TURNO_CHOICES,
        blank=True,
        default="",
        verbose_name="Turno",
        help_text="Deixe em branco para períodos comuns a todos os turnos (ex.: Intervalo).",
    )

    class Meta:
        ordering = ["turno", "posicao", "id"]
        verbose_name = "Ordem de Horário"
        verbose_name_plural = "Ordens de Horário"

    def __str__(self):
        if self.turno:
            return f"{self.ordem} ({self.get_turno_display()})"
        return self.ordem

    @property
    def faixa(self):
        if self.inicio and self.termino:
            return f"{self.inicio.strftime('%H:%M')} - {self.termino.strftime('%H:%M')}"
        return ""


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
        Professor, on_delete=models.CASCADE, related_name="horarios",
        null=True, blank=True,
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="horarios",
        null=True, blank=True,
    )

    class Meta:
        ordering = ["turma", "dia__ordem", "ordem__posicao"]
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


class PerfilUsuario(models.Model):
    """Perfil estendido — liga User à Escola e define papel/hierarquia.

    Mantemos o User padrão do Django intocado e adicionamos esta tabela nova
    para que o robô do Bernoulli (que NÃO mexe em User nem em PerfilUsuario)
    siga funcionando sem qualquer alteração.
    """

    PAPEL_ALUNO        = "aluno"
    PAPEL_RESPONSAVEL  = "responsavel"
    PAPEL_PROFESSOR    = "professor"
    PAPEL_COORDENADOR  = "coordenador"
    PAPEL_ADMIN_ESCOLA = "admin_escola"
    PAPEL_SUPERADMIN   = "superadmin"

    PAPEL_CHOICES = [
        (PAPEL_ALUNO,        "Aluno"),
        (PAPEL_RESPONSAVEL,  "Responsável"),
        (PAPEL_PROFESSOR,    "Professor"),
        (PAPEL_COORDENADOR,  "Coordenador"),
        (PAPEL_ADMIN_ESCOLA, "Administrador da Escola"),
        (PAPEL_SUPERADMIN,   "Super-admin"),
    ]

    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="perfil"
    )
    escola = models.ForeignKey(
        Escola, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="perfis", verbose_name="Escola padrão",
    )
    escolas_extras = models.ManyToManyField(
        Escola, blank=True, related_name="perfis_extras",
        help_text="Outras escolas que este usuário pode acessar (multi-unidade).",
    )
    papel = models.CharField(
        max_length=20, choices=PAPEL_CHOICES, default=PAPEL_RESPONSAVEL,
    )
    professor_vinculado = models.ForeignKey(
        Professor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="usuarios_vinculados",
        help_text="Quando preenchido, formulários já vêm com este professor selecionado.",
    )

    class Meta:
        verbose_name = "Perfil do Usuário"
        verbose_name_plural = "Perfis dos Usuários"

    def __str__(self):
        return f"{self.usuario.username} ({self.get_papel_display()})"

    # ── Helpers ───────────────────────────────────────────────────────────
    def escolas_visiveis(self):
        """Retorna queryset de escolas que o usuário pode ver."""
        ids = set()
        if self.escola_id:
            ids.add(self.escola_id)
        ids.update(self.escolas_extras.values_list("id", flat=True))
        if self.papel == self.PAPEL_SUPERADMIN or not ids:
            return Escola.objects.all()
        return Escola.objects.filter(id__in=ids)

    @property
    def is_admin_escola(self):
        return self.papel in (
            self.PAPEL_ADMIN_ESCOLA,
            self.PAPEL_COORDENADOR,
            self.PAPEL_SUPERADMIN,
        )


class ProfessorUsuario(models.Model):
    """Histórico de usuários que utilizam/utilizaram o perfil de um Professor.

    Ao trocar o usuário do professor, o vínculo anterior é encerrado
    (data_fim preenchida) e um novo é criado, preservando o histórico
    sem perder informações já vinculadas ao Professor.
    """

    professor = models.ForeignKey(
        Professor, on_delete=models.CASCADE, related_name="vinculos_usuarios"
    )
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="vinculos_professor"
    )
    data_inicio = models.DateField(verbose_name="Início do vínculo")
    data_fim = models.DateField(
        null=True, blank=True, verbose_name="Fim do vínculo",
        help_text="Deixe em branco enquanto o vínculo estiver ativo.",
    )
    ativo = models.BooleanField(default=True)
    observacao = models.TextField(blank=True, verbose_name="Observação")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ativo", "-data_inicio"]
        verbose_name = "Vínculo Professor ↔ Usuário"
        verbose_name_plural = "Vínculos Professor ↔ Usuário"

    def __str__(self):
        estado = "ativo" if self.ativo else "encerrado"
        return f"{self.usuario.username} → {self.professor.nome_professor} ({estado})"

    def encerrar(self, data_fim=None):
        from datetime import date
        self.data_fim = data_fim or date.today()
        self.ativo = False
        self.save()


class Monitoria(models.Model):
    """Programação de monitorias por escola.

    Cada registro corresponde a um horário de monitoria oferecido por
    um(a) docente, em um determinado dia da semana, sala e nível de ensino.
    """

    escola = models.ForeignKey(
        Escola, on_delete=models.CASCADE, related_name="monitorias"
    )
    professor = models.ForeignKey(
        Professor, on_delete=models.CASCADE, related_name="monitorias",
        verbose_name="Docente",
    )
    materia = models.ForeignKey(
        Materia, on_delete=models.CASCADE, related_name="monitorias",
        verbose_name="Componente curricular",
    )
    dia = models.ForeignKey(
        Dias, on_delete=models.CASCADE, related_name="monitorias",
        verbose_name="Dia da semana",
    )
    hora_inicio = models.TimeField(verbose_name="Início")
    hora_fim = models.TimeField(verbose_name="Término")
    sala = models.CharField(max_length=30, verbose_name="Sala")
    nivel_ensino = models.CharField(
        max_length=80, blank=True, default="",
        verbose_name="Nível de ensino",
        help_text="Texto livre. Ex.: Ensino Fundamental, Ensino Médio, 9º ano...",
    )
    observacao = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["escola", "dia__ordem", "hora_inicio"]
        verbose_name = "Monitoria"
        verbose_name_plural = "Monitorias"

    def __str__(self):
        return f"{self.professor} — {self.materia} — {self.dia} {self.faixa_horaria}"

    @property
    def faixa_horaria(self):
        return f"{self.hora_inicio.strftime('%Hh%M')} às {self.hora_fim.strftime('%Hh%M')}"


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
