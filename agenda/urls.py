from django.urls import path
from .views import views_user
from .views import views_tarefas
from .views import views_aluno
from .views import views_escola
from .views import views_turma
from .views import views_conexao
from .views import views_agenda
from .views import views_whats
from .views import views_robo

app_name = 'cal'

urlpatterns = [

    # ─── Página inicial e estáticas ────────────────────────────────────────────
    path('', views_user.bemvindo, name='bemvindo'),
    path('home/', views_user.home, name='home'),
    path('contato/', views_user.contato, name='contato'),
    path('manual/', views_user.manual_publico, name='manual_publico'),

    # ─── Usuários ──────────────────────────────────────────────────────────────
    path('usuarios/', views_user.listar_usuarios, name='listar_usuarios'),
    path('usuarios/adicionar/', views_user.adicionar_usuario, name='adicionar_usuario'),
    path('usuarios/<int:user_id>/editar/', views_user.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:user_id>/excluir/', views_user.excluir_usuario, name='excluir_usuario'),
    path('usuarios/<int:user_id>/resetar-senha/', views_user.resetar_senha, name='resetar_senha'),
    path('usuarios/<int:user_id>/desativar/', views_user.desativar_usuario, name='desativar_usuario'),
    path('perfil/', views_user.perfil_usuario, name='perfil'),

    # ─── Escolas ───────────────────────────────────────────────────────────────
    path('escolas/', views_escola.escola_list, name='escola_list'),
    path('escolas/nova/', views_escola.escola_nova, name='escola_nova'),
    path('escolas/<int:pk>/editar/', views_escola.escola_update, name='escola_update'),
    path('escolas/<int:pk>/excluir/', views_escola.escola_delete, name='escola_delete'),

    # ─── Turmas ────────────────────────────────────────────────────────────────
    path('turmas/', views_turma.turma_list, name='turma_list'),
    path('turmas/nova/', views_turma.turma_create, name='turma_create'),
    path('turmas/<int:pk>/editar/', views_turma.turma_update, name='turma_update'),
    path('turmas/<int:pk>/excluir/', views_turma.turma_delete, name='turma_delete'),

    # ─── Alunos ────────────────────────────────────────────────────────────────
    path('alunos/', views_aluno.aluno_list, name='aluno_list'),
    path('alunos/novo/', views_aluno.aluno_create, name='aluno_create'),
    path('alunos/<int:pk>/editar/', views_aluno.aluno_update, name='aluno_update'),
    path('alunos/<int:pk>/excluir/', views_aluno.aluno_delete, name='aluno_delete'),

    # ─── Conexões Agenda ───────────────────────────────────────────────────────
    path('conexoes/', views_conexao.conexao_list, name='conexao_list'),
    path('conexoes/nova/', views_conexao.conexao_create, name='conexao_create'),
    path('conexoes/<int:pk>/editar/', views_conexao.conexao_update, name='conexao_update'),
    path('conexoes/<int:pk>/excluir/', views_conexao.conexao_delete, name='conexao_delete'),

    # ─── Eventos da Agenda ─────────────────────────────────────────────────────
    path('eventos/', views_agenda.agenda_list, name='agenda_list'),
    path('eventos/novo/', views_agenda.agenda_create, name='agenda_create'),
    path('eventos/<int:pk>/editar/', views_agenda.agenda_update, name='agenda_update'),
    path('eventos/<int:pk>/excluir/', views_agenda.agenda_delete, name='agenda_delete'),

    # ─── WhatsApp Envios ───────────────────────────────────────────────────────
    path('whatsapp/', views_whats.whats_list, name='whats_list'),
    path('whatsapp/novo/', views_whats.whats_create, name='whats_create'),
    path('whatsapp/<int:pk>/editar/', views_whats.whats_update, name='whats_update'),
    path('whatsapp/<int:pk>/excluir/', views_whats.whats_delete, name='whats_delete'),

    # ─── Tarefas ───────────────────────────────────────────────────────────────
    path('tarefas/', views_tarefas.listar_tarefas, name='listar_tarefas'),
    path('tarefa/concluir/', views_tarefas.marcar_concluida, name='marcar_concluida'),

    # ─── Robô ──────────────────────────────────────────────────────────────────
    path('robo/executar/', views_robo.executar_robo, name='executar_robo'),
    path('robo/status/', views_robo.status_robo, name='status_robo'),
]
