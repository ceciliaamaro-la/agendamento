"""Popula o sistema com dados de demonstração: matérias comuns,
professores, livros, usuários (senha padrão 123456) e vínculos.

Uso:
    python manage.py seed_demo_data

Idempotente: pode ser executado várias vezes sem duplicar dados.
"""
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from agenda.models import (
    Aluno,
    Dias,
    Escola,
    Livro,
    Materia,
    Monitoria,
    OrdemHorario,
    PerfilUsuario,
    Professor,
    ProfessorUsuario,
    Turma,
)

SENHA_PADRAO = "123456"

MATERIAS_COMUNS = [
    "Português",
    "Matemática",
    "Inglês",
    "Espanhol",
    "História",
    "Geografia",
    "Ciências",
    "Física",
    "Química",
    "Biologia",
    "Educação Física",
    "Artes",
    "Filosofia",
    "Sociologia",
    "Redação",
]

DIAS_SEMANA = [
    ("Segunda", 1),
    ("Terça", 2),
    ("Quarta", 3),
    ("Quinta", 4),
    ("Sexta", 5),
    ("Sábado", 6),
    ("Domingo", 7),
]

LIVRO_POR_MATERIA = {
    "Português": "Português Linguagens",
    "Matemática": "Matemática Contexto e Aplicações",
    "Inglês": "English in Action",
    "Espanhol": "Cercanía Joven",
    "História": "Caminhos do Homem",
    "Geografia": "Geografia Geral e do Brasil",
    "Ciências": "Ciências - Projeto Teláris",
    "Física": "Física Aula por Aula",
    "Química": "Química Cidadã",
    "Biologia": "Bio - Sônia Lopes",
    "Educação Física": "Práticas Corporais",
    "Artes": "Por Toda Parte",
    "Filosofia": "Filosofando",
    "Sociologia": "Sociologia em Movimento",
    "Redação": "Redação Inquieta",
}

NOMES_PROF = {
    "Português": "Ana Silva",
    "Matemática": "Carlos Oliveira",
    "Inglês": "Beatriz Lima",
    "Espanhol": "Juan Carrasco",
    "História": "Roberto Mendes",
    "Geografia": "Marina Costa",
    "Ciências": "Paulo Henrique",
    "Física": "Felipe Almeida",
    "Química": "Renata Souza",
    "Biologia": "Camila Ferreira",
    "Educação Física": "Marcelo Ramos",
    "Artes": "Helena Duarte",
    "Filosofia": "Eduardo Pires",
    "Sociologia": "Lucia Martins",
    "Redação": "Patrícia Nunes",
}

# Usuário demo: (username, papel, professor_da_materia, escola_nome)
# professor_da_materia=None significa que não é professor
USUARIOS_DEMO = [
    # Coordenação / administração
    ("coord_lasalle", PerfilUsuario.PAPEL_COORDENADOR, None, "LaSalle"),
    ("admin_escolap", PerfilUsuario.PAPEL_ADMIN_ESCOLA, None, "Escola P"),
    # Professores (vinculados a um Professor cadastrado)
    ("prof_ingles", PerfilUsuario.PAPEL_PROFESSOR, "Inglês", "LaSalle"),
    ("prof_historia", PerfilUsuario.PAPEL_PROFESSOR, "História", "LaSalle"),
    ("prof_geografia", PerfilUsuario.PAPEL_PROFESSOR, "Geografia", "LaSalle"),
    ("prof_ciencias", PerfilUsuario.PAPEL_PROFESSOR, "Ciências", "LaSalle"),
    ("prof_fisica", PerfilUsuario.PAPEL_PROFESSOR, "Física", "LaSalle"),
    ("prof_quimica", PerfilUsuario.PAPEL_PROFESSOR, "Química", "LaSalle"),
    ("prof_biologia", PerfilUsuario.PAPEL_PROFESSOR, "Biologia", "LaSalle"),
    ("prof_artes", PerfilUsuario.PAPEL_PROFESSOR, "Artes", "LaSalle"),
    ("prof_edfisica", PerfilUsuario.PAPEL_PROFESSOR, "Educação Física", "LaSalle"),
    ("prof_redacao", PerfilUsuario.PAPEL_PROFESSOR, "Redação", "LaSalle"),
    # Alunos / responsáveis demo
    ("aluno_demo1", PerfilUsuario.PAPEL_ALUNO, None, "LaSalle"),
    ("aluno_demo2", PerfilUsuario.PAPEL_ALUNO, None, "LaSalle"),
    ("resp_demo1", PerfilUsuario.PAPEL_RESPONSAVEL, None, "LaSalle"),
    ("resp_demo2", PerfilUsuario.PAPEL_RESPONSAVEL, None, "LaSalle"),
]


class Command(BaseCommand):
    help = "Popula o sistema com dados de demonstração (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        out = self.stdout

        # ── Escolas (garante que existam) ────────────────────────────
        escolas = {}
        for nome in ["LaSalle", "Escola P"]:
            escola, created = Escola.objects.get_or_create(nome_escola=nome)
            escolas[nome] = escola
            if created:
                out.write(self.style.SUCCESS(f"+ Escola: {nome}"))

        # ── Dias da semana ──────────────────────────────────────────
        for nome, ordem in DIAS_SEMANA:
            obj, created = Dias.objects.get_or_create(
                dias=nome, defaults={"ordem": ordem}
            )
            if not created and obj.ordem != ordem:
                obj.ordem = ordem
                obj.save(update_fields=["ordem"])
            if created:
                out.write(self.style.SUCCESS(f"+ Dia: {nome}"))

        # ── Matérias comuns ─────────────────────────────────────────
        materias = {}
        for nome in MATERIAS_COMUNS:
            mat, created = Materia.objects.get_or_create(nome_materia=nome)
            materias[nome] = mat
            if created:
                out.write(self.style.SUCCESS(f"+ Matéria: {nome}"))

        # ── Professores e Livros para cada escola × matéria ─────────
        professores = {}  # (escola, materia) -> Professor
        for esc_nome, escola in escolas.items():
            for mat_nome, materia in materias.items():
                nome_prof = f"{NOMES_PROF[mat_nome]} ({esc_nome})"
                prof, created = Professor.objects.get_or_create(
                    escola=escola,
                    materia=materia,
                    nome_professor=nome_prof,
                )
                professores[(esc_nome, mat_nome)] = prof
                if created:
                    out.write(
                        self.style.SUCCESS(
                            f"+ Professor: {nome_prof} — {mat_nome}"
                        )
                    )

                nome_livro = LIVRO_POR_MATERIA[mat_nome]
                Livro.objects.get_or_create(
                    escola=escola, materia=materia, nome_livro=nome_livro,
                )

        # ── Períodos / Ordens de horário (Matutino padrão) ──────────
        periodos_matutino = [
            ("1ª Aula", 1, "07:10", "08:00"),
            ("2ª Aula", 2, "08:00", "08:50"),
            ("Intervalo", 3, "08:50", "09:10"),
            ("3ª Aula", 4, "09:10", "10:00"),
            ("4ª Aula", 5, "10:00", "10:50"),
            ("5ª Aula", 6, "10:50", "11:40"),
        ]
        for nome, pos, ini, fim in periodos_matutino:
            OrdemHorario.objects.get_or_create(
                ordem=nome, turno="M",
                defaults={
                    "posicao": pos,
                    "inicio": ini,
                    "termino": fim,
                },
            )

        # ── Usuários demo (senha = 123456) ──────────────────────────
        criados_users = []
        for username, papel, mat_nome, esc_nome in USUARIOS_DEMO:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": username.replace("_", " ").title(),
                },
            )
            # garante senha padrão (sempre, mesmo se já existia)
            user.set_password(SENHA_PADRAO)
            user.save()

            escola = escolas.get(esc_nome) if esc_nome else None
            perfil, _ = PerfilUsuario.objects.get_or_create(
                usuario=user,
                defaults={"papel": papel, "escola": escola},
            )
            perfil.papel = papel
            if escola:
                perfil.escola = escola

            # Vincula professor (se aplicável)
            if mat_nome and esc_nome:
                prof = professores.get((esc_nome, mat_nome))
                if prof:
                    perfil.professor_vinculado = prof
                    # Histórico ProfessorUsuario (encerra ativos prévios)
                    ProfessorUsuario.objects.filter(
                        professor=prof, ativo=True,
                    ).exclude(usuario=user).update(
                        ativo=False, data_fim=date.today()
                    )
                    ProfessorUsuario.objects.get_or_create(
                        professor=prof, usuario=user, ativo=True,
                        defaults={"data_inicio": date.today()},
                    )
            perfil.save()

            if created:
                criados_users.append(username)
                out.write(self.style.SUCCESS(f"+ Usuário: {username} ({papel})"))

        # ── Vincula alguns alunos demo a usuários "aluno_demo*" ─────
        turmas_lasalle = list(Turma.objects.filter(escola=escolas["LaSalle"]))
        if turmas_lasalle:
            turma_alvo = turmas_lasalle[0]
            for username, nome_aluno in [
                ("aluno_demo1", "Aluno Demo 1"),
                ("aluno_demo2", "Aluno Demo 2"),
            ]:
                user = User.objects.filter(username=username).first()
                if not user:
                    continue
                aluno, _ = Aluno.objects.get_or_create(
                    nome_aluno=nome_aluno,
                    defaults={"turma": turma_alvo},
                )
                aluno.usuarios.add(user)

        # ── Monitoria de exemplo (opcional, idempotente) ────────────
        seg = Dias.objects.filter(dias="Segunda").first()
        if seg:
            prof_mat = professores.get(("LaSalle", "Matemática"))
            if prof_mat:
                Monitoria.objects.get_or_create(
                    escola=escolas["LaSalle"],
                    professor=prof_mat,
                    materia=materias["Matemática"],
                    dia=seg,
                    hora_inicio="14:00",
                    hora_fim="15:00",
                    defaults={"sala": "Sala 12", "nivel_ensino": "Ensino Médio"},
                )

        out.write("")
        out.write(self.style.SUCCESS("Concluído!"))
        out.write(
            f"Senha padrão de TODOS os usuários demo: {SENHA_PADRAO}"
        )
        out.write(
            f"Novos usuários criados nesta execução: "
            f"{', '.join(criados_users) if criados_users else 'nenhum'}"
        )
