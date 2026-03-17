from django.contrib import admin
from .models import (
    Escola,
    Turma,
    Aluno,
    ConexaoAgenda,
    AgendaEvento,
    TarefaCompleta,
    WhatsAppEnvio,
)


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ("nome_escola", "criado_em")
    search_fields = ("nome_escola",)


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome_turma", "escola", "criado_em")
    list_filter = ("escola",)
    search_fields = ("nome_turma",)


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("nome_aluno", "turma", "criado_em")
    list_filter = ("turma",)
    search_fields = ("nome_aluno",)
    filter_horizontal = ("usuarios",)


@admin.register(ConexaoAgenda)
class ConexaoAgendaAdmin(admin.ModelAdmin):
    list_display = ("turma", "login", "ativo", "criado_em")
    list_filter = ("ativo",)


@admin.register(AgendaEvento)
class AgendaEventoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "data", "turma", "enviado_whatsapp", "criado_em")
    list_filter = ("tipo", "turma", "enviado_whatsapp")
    search_fields = ("titulo", "descricao")
    ordering = ("-data",)


@admin.register(TarefaCompleta)
class TarefaCompletaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "evento", "concluida", "atualizado_em")
    list_filter = ("concluida", "aluno__turma")
    search_fields = ("aluno__nome_aluno", "evento__titulo")


@admin.register(WhatsAppEnvio)
class WhatsAppEnvioAdmin(admin.ModelAdmin):
    list_display = ("turma", "hash_evento", "enviado_em")
    list_filter = ("turma",)
