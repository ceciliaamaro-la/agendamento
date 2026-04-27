# Agenda Escolar — Django 5.2

## Objetivo
Sistema de acompanhamento de eventos escolares. Faz scraping da plataforma Bernoulli com Playwright, armazena eventos em SQLite, e envia notificações WhatsApp via Evolution API. Inclui módulos pedagógicos: turmas, alunos, professores, matérias, livros, horários (grade), aulas/diário, monitorias e vínculos Professor↔Usuário.

## Stack
- **Backend**: Django 5.2 + SQLite
- **Scraping**: Playwright (async)
- **WhatsApp**: Evolution API (desativado temporariamente)
- **Frontend**: Bootstrap 5 + Bootstrap Icons + JS vanilla (cascata)
- **PDF**: ReportLab
- **Deploy**: gunicorn (produção), `manage.py runserver 0.0.0.0:5000` (dev)

## Estrutura de Apps
- `agenda/` — app principal: modelos, views, serviços, admin
- `evolution/` — integração com Evolution API para WhatsApp
- `core/` — configurações Django e urls raiz

## Modelos
- `Escola` — escolas cadastradas
- `Turma` — turmas vinculadas à escola
  - **Campo `turno`** (M=Matutino, V=Vespertino, N=Noturno, I=Integral): obrigatório no formulário; permite separar turmas como 181M e 181V
- `Aluno` — alunos com telefone/email; M2M `usuarios` (responsáveis)
- `ConexaoAgenda` — credenciais Bernoulli por turma (campo `ativo`)
- `AgendaEvento` — eventos scraped + manuais (título, data, tipo, hash único, campos pedagógicos opcionais)
- `TarefaCompleta` — aluno + evento, marca se concluído (unique_together) + flag `visivel`
- `WhatsAppEnvio` — controle de envios por turma+hash
- `Materia` — matérias (catálogo global)
- `Professor` — vinculado a Escola/Matéria; informações pedagógicas (Aulas, Horários, Monitorias) referenciam Professor (não User), preservando dados quando o usuário muda
- `ProfessorUsuario` — histórico de quem usou o perfil de cada Professor (data_inicio, data_fim, ativo). Ao criar/editar um vínculo ativo, vínculos ativos anteriores do mesmo professor são automaticamente encerrados
- `Livro` — livros didáticos por escola/matéria
- `Dias` — dias da semana com `ordem` (Seg=1...)
- `OrdemHorario` — períodos da grade (1ª Aula, Intervalo, ...)
  - **Campo `turno`** (M/V/N/I, ou em branco para "comum a todos os turnos"): permite ter "1ª Aula 07:10 Matutino" e "1ª Aula 13:10 Vespertino" como entradas distintas; itens sem turno (Intervalo, Almoço) servem para qualquer turma
  - **Campo `escola`** (FK opcional): se NULL → período GLOBAL (visível em todas as escolas, gerenciado apenas por superadmin); se preenchido → período específico da escola, gerenciável pelo admin_escola correspondente
- `LogAuditoria` — registro de ações críticas (criar/excluir usuário, mudar papel, resetar senha, desativar usuário, excluir escola); visível apenas ao superadmin em `/auditoria/`
- `Horario` — célula da grade: escola + turma + dia + ordem + (professor opc.) + (matéria opc.)
- `Aula` — registro de aula ministrada (conteúdo, dever, datas)
- `DiarioAluno` — chamada/diário por aula × aluno
- `Monitoria` — programação de monitorias por escola
- `PerfilUsuario` — papel + escola(s) visíveis + professor_vinculado

## Papéis (PerfilUsuario)
Definidos em `agenda/services/escopo.py`:
- `superadmin` — vê e administra TUDO (também `is_superuser`/`is_staff`); único que vê `/auditoria/` e gerencia períodos globais
- `admin_escola` — administra conteúdo das escolas vinculadas ao perfil (CRUD completo)
- `coordenador` — **somente leitura** em todas as áreas administrativas (mesma visão do admin_escola, mas sem botões/URLs de criar/editar/excluir)
- `professor` — vê/edita só as próprias aulas/diários
- `aluno` / `responsavel` — leitura das tarefas/horário/diário das turmas vinculadas

### Decoradores de escopo (`agenda/services/escopo.py`)
- `admin_escola_required` — admin_escola, coordenador ou superadmin (LIST)
- `admin_estrito_required` — admin_escola/superadmin (CRIAR/EDITAR/EXCLUIR; bloqueia coordenador)
- `_negar(request, msg)` — helper que dispara `messages.error` + redirect para a home, em vez de `HttpResponseForbidden` 403 (UX consistente)

## Programação de Monitorias
- `/monitorias/` — visualização pública (todos os logados) em formato pivotado: linha por (Professor × Componente), colunas pelos dias da semana
- `/monitorias/gerenciar/`, `/monitorias/nova/` — CRUD restrito a admin/coordenação (admin_escola_required)
- `/vinculos-professor/` — gestão de histórico de vínculos Professor↔Usuário (admin_escola)

## URLs principais
- `/` — home (requer login para ver painel)
- `/login/`, `/logout/`, `/register/` — autenticação
- `/escolas/`, `/turmas/`, `/alunos/`, `/professores/`, `/materias/`, `/livros/` — CRUDs pedagógicos
- `/periodos/` — CRUD de OrdemHorario, agrupado por escola (Global/escola_X) e por turno
- `/auditoria/` — log de ações críticas (somente superadmin)
- `/horarios/`, `/horarios/novo/`, `/horarios/pdf/` — grade da turma; `novo/` filtra ordens pelo turno da turma escolhida
- `/eventos/`, `/aulas/`, `/diario/` — eventos da agenda, aulas, diário/chamada
- `/conexoes/` — credenciais Bernoulli
- `/whatsapp/` — controle de envios
- `/tarefas/<aluno_id>/`, `/tarefa/concluir/`, `/tarefa/ocultar/` — tarefas do aluno
- `/monitorias/`, `/monitorias/gerenciar/`, `/monitorias/nova/` — monitorias
- `/vinculos-professor/` — vínculos Professor↔Usuário
- `/usuarios/`, `/perfil/` — gestão de usuários
- `/admin/` — Django Admin

## Endpoints AJAX (cascata de formulários)
`agenda/views/views_cascade.py` — preenche selects relacionados em Aula/Evento/Horário:
- `/api/cascade/professor/<pk>/` — devolve escola, matérias e turmas (todas da escola do professor) e livros
- `/api/cascade/turma/<pk>/` — devolve escola, professores (todos da escola), matérias (todos da escola) e ordens (filtradas pelo turno da turma + comuns)
- `/api/cascade/materia/<pk>/` — devolve professores e livros da matéria
- JS: `static/js/cascade.js`. Regras importantes:
  - Nunca substitui a turma se o usuário já escolheu uma (evita sobrescrita silenciosa)
  - Atualiza dinamicamente o select de "ordem" (período) ao trocar de turma

## Serviços
- `agenda/services/sync_agenda.py` — sincroniza eventos via scraping
- `agenda/services/envio_service.py` — agrupa e envia mensagens WhatsApp por turma
- `agenda/services/salvar_eventos_service.py` — salva eventos no banco
- `agenda/services/escopo.py` — helpers de papéis/escopo (querysets filtrados, decorators, `aplicar_escopo_no_form`)
- `agenda/agenda_robot.py` — Playwright scraper do Bernoulli

## Configuração
- `ALLOWED_HOSTS = ['*']`
- `CSRF_TRUSTED_ORIGINS` configurado para Replit
- `django.contrib.humanize` em INSTALLED_APPS
- Workflow: `python3.11 manage.py runserver 0.0.0.0:5000` (porta 5000 → externa 80)

## WhatsApp
- Envio temporariamente desativado em `sync_agenda.py` (comentado)
- Evolution API configurada via env vars `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`

## Migrations aplicadas
- 0001_initial
- 0002_conexaoagenda_ativo
- 0003_update_whatsappenvio
- 0004_tarefacompleta
- 0005_aluno_m2m_usuarios_remove_campos
- 0006_aluno_add_telefone
- 0007_agendaevento_add_inicio_termino_tem_anexo
- 0008_tarefacompleta_add_visivel
- 0009_add_url_anexo_to_agendaevento
- 0010_add_diario_modelos
- 0011_conexao_fk_to_o2o
- 0012_populate_dias_ordemhorario
- 0013_agendaevento_aula_agendaevento_conteudo_and_more
- 0014_perfilusuario
- 0015_alter_horario_materia_alter_horario_professor
- 0016_alter_horario_options_alter_ordemhorario_options_and_more
- 0017_monitoria_professorusuario
- 0018_alter_monitoria_nivel_ensino
- 0019_turma_turno (auto-popula turno pelo sufixo M/V do nome_turma)
- 0020_ordemhorario_turno (auto-popula turno pelo horário de início: <12h M, <18h V, ≥18h N)

## Convenções de UI
- Tempos exibidos em formato 24h com sufixo "H" em /periodos/ (ex.: `13:10 H`)
- Turnos exibidos como badges coloridos: Matutino (warning/sunrise), Vespertino (info/sun), Noturno (dark/moon), Integral (secondary/clock)
- Formulários usam classes Bootstrap padronizadas (`form-control shadow-sm` ou `form-select shadow-sm`)
- Cards e tabelas com `shadow-sm`; ações com ícones Bootstrap Icons

## Histórico recente de mudanças relevantes
- Importação Replit Agent → Replit concluída (instaladas dependências do `requirements.txt`)
- Adicionado campo `turno` em `Turma` e `OrdemHorario` com migrações de auto-população
- Corrigido bug da cascata JS que sobrescrevia a turma escolhida pelo usuário (181V → 181M)
- Cascata `cascade_turma` agora retorna todos os professores/matérias da escola (não só os com horário já cadastrado)
- Cascata `cascade_professor` agora retorna todas as turmas da escola
- Formulário de Horário filtra ordens (períodos) pelo turno da turma escolhida; ordens "comuns" (sem turno) sempre aparecem
- /periodos/ agrupa visualmente por turno e mostra horários no formato `13:10 H`
