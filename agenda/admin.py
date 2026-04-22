from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Escola,
    Turma,
    Aluno,
    ConexaoAgenda,
    AgendaEvento,
    TarefaCompleta,
    WhatsAppEnvio,
    PerfilUsuario,
    Professor,
    Materia,
    Livro,
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


# ── Cadastros pedagógicos (necessários para autocomplete do PerfilUsuario) ──
@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ("nome_materia",)
    search_fields = ("nome_materia",)


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ("nome_professor", "materia", "escola")
    list_filter = ("escola", "materia")
    search_fields = ("nome_professor",)
    autocomplete_fields = ("escola", "materia")


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ("nome_livro", "materia", "escola")
    list_filter = ("escola", "materia")
    search_fields = ("nome_livro",)
    autocomplete_fields = ("escola", "materia")


# ── Perfil estendido inline no User do Django ──────────────────────────────
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    fk_name = "usuario"
    autocomplete_fields = ("escola", "professor_vinculado")
    filter_horizontal = ("escolas_extras",)
    fields = ("papel", "escola", "escolas_extras", "professor_vinculado")
    extra = 0


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "papel", "escola", "professor_vinculado")
    list_filter = ("papel", "escola")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name")
    autocomplete_fields = ("usuario", "escola", "professor_vinculado")
    filter_horizontal = ("escolas_extras",)


# Re-registra User com o inline do perfil
class UserAdmin(BaseUserAdmin):
    inlines = (PerfilUsuarioInline,)
    list_display = BaseUserAdmin.list_display + ("get_papel", "get_escola")

    @admin.display(description="Papel")
    def get_papel(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.get_papel_display() if perfil else "—"

    @admin.display(description="Escola")
    def get_escola(self, obj):
        perfil = getattr(obj, "perfil", None)
        return perfil.escola if perfil and perfil.escola_id else "—"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
