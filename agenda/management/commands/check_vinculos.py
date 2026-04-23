"""Verifica e (opcionalmente) corrige inconsistências entre
PerfilUsuario.professor_vinculado e ProfessorUsuario (fonte oficial).

Uso:
    python manage.py check_vinculos          # apenas relatório
    python manage.py check_vinculos --fix    # corrige sincronizando o perfil
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from agenda.models import PerfilUsuario, ProfessorUsuario


class Command(BaseCommand):
    help = (
        "Audita a coerência entre PerfilUsuario.professor_vinculado (cache) "
        "e ProfessorUsuario (fonte oficial). Use --fix para corrigir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Corrige o perfil para refletir o vínculo ativo mais recente.",
        )

    def handle(self, *args, **opts):
        fix = opts["fix"]
        problemas = []

        for user in User.objects.all().order_by("username"):
            perfil = getattr(user, "perfil", None)
            cache_id = perfil.professor_vinculado_id if perfil else None
            vinculo_ativo = (
                ProfessorUsuario.objects
                .filter(usuario=user, ativo=True)
                .order_by("-data_inicio", "-id")
                .first()
            )
            oficial_id = vinculo_ativo.professor_id if vinculo_ativo else None

            # Detecta inconsistências
            if cache_id != oficial_id:
                problemas.append((user, perfil, cache_id, oficial_id, vinculo_ativo))
            # Múltiplos vínculos ativos para o mesmo usuário (suspeito)
            ativos = ProfessorUsuario.objects.filter(
                usuario=user, ativo=True
            ).count()
            if ativos > 1:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ {user.username}: {ativos} vínculos ATIVOS simultâneos"
                ))

        if not problemas:
            self.stdout.write(self.style.SUCCESS(
                "✓ Tudo coerente: PerfilUsuario.professor_vinculado bate com "
                "ProfessorUsuario para todos os usuários."
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"\n{len(problemas)} inconsistência(s) encontrada(s):\n"
        ))
        for user, perfil, cache_id, oficial_id, vinculo in problemas:
            self.stdout.write(
                f"  • {user.username:20s}  perfil.professor_vinculado={cache_id!s:>5}  "
                f"oficial(ProfessorUsuario)={oficial_id!s:>5}"
            )

        if not fix:
            self.stdout.write(self.style.NOTICE(
                "\nRode novamente com --fix para corrigir o cache do perfil."
            ))
            return

        corrigidos = 0
        for user, perfil, cache_id, oficial_id, vinculo in problemas:
            if perfil is None:
                perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.professor_vinculado_id = oficial_id
            perfil.save(update_fields=["professor_vinculado"])
            corrigidos += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ {corrigidos} perfil(is) sincronizado(s) com a fonte oficial."
        ))
