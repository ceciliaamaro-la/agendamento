"""Sinais do app agenda.

1) Cria PerfilUsuario automaticamente para todo User.
2) Mantém PerfilUsuario.professor_vinculado em sincronia com ProfessorUsuario
   (que é a FONTE OFICIAL do vínculo Professor↔Usuário). O campo no perfil
   funciona apenas como atalho/cache para os formulários e selects.
"""

from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import PerfilUsuario, ProfessorUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    PerfilUsuario.objects.get_or_create(usuario=instance)


def _sincronizar_perfil_a_partir_de_vinculos(usuario):
    """Atualiza PerfilUsuario.professor_vinculado conforme o vínculo ATIVO
    mais recente em ProfessorUsuario para o usuário informado."""
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    vinculo_ativo = (
        ProfessorUsuario.objects
        .filter(usuario=usuario, ativo=True)
        .order_by("-data_inicio", "-id")
        .first()
    )
    novo_prof_id = vinculo_ativo.professor_id if vinculo_ativo else None
    if perfil.professor_vinculado_id != novo_prof_id:
        perfil.professor_vinculado_id = novo_prof_id
        perfil.save(update_fields=["professor_vinculado"])


@receiver(post_save, sender=ProfessorUsuario)
def sincronizar_perfil_apos_vinculo(sender, instance, **kwargs):
    _sincronizar_perfil_a_partir_de_vinculos(instance.usuario)


@receiver(post_delete, sender=ProfessorUsuario)
def sincronizar_perfil_apos_remocao_vinculo(sender, instance, **kwargs):
    _sincronizar_perfil_a_partir_de_vinculos(instance.usuario)
