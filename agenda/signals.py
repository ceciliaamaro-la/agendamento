"""Sinais — cria PerfilUsuario automaticamente para todo User criado."""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)
    else:
        PerfilUsuario.objects.get_or_create(usuario=instance)
