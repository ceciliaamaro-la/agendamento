from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from ..forms import UsuarioForm, UsuarioUpdateForm, UsuarioPasswordResetForm
from ..models import PerfilUsuario, LogAuditoria
from ..services.auditoria import registrar as registrar_auditoria
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


def bemvindo(request):
    if request.user.is_authenticated:
        return redirect('cal:home')
    return render(request, 'bemvindo.html')


@login_required
def perfil_usuario(request):
    from ..services.escopo import is_admin_escola
    pode_editar_username = is_admin_escola(request.user)

    def _build_form(*args, **kwargs):
        f = UsuarioUpdateForm(*args, **kwargs)
        if not pode_editar_username and 'username' in f.fields:
            f.fields['username'].disabled = True
            f.fields['username'].help_text = 'Apenas administradores/coordenadores podem alterar o nome de usuário.'
        return f

    if request.method == 'POST':
        form = _build_form(request.POST, instance=request.user)
        nova_senha = (request.POST.get('nova_senha') or '').strip()
        confirmar_senha = (request.POST.get('confirmar_senha') or '').strip()
        senha_ok = True
        senha_erro = None
        if nova_senha or confirmar_senha:
            if nova_senha != confirmar_senha:
                senha_ok = False
                senha_erro = 'As senhas não coincidem.'
        if form.is_valid() and senha_ok:
            user = form.save()
            if nova_senha:
                user.set_password(nova_senha)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Perfil e senha atualizados com sucesso!')
            else:
                messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('cal:perfil')
        if senha_erro:
            messages.error(request, senha_erro)
    else:
        form = _build_form(instance=request.user)

    return render(request, 'user/form_usuario.html', {
        'form': form,
        'titulo': 'Meu Perfil'
    })


@login_required
def editar_usuario(request, user_id):
    from ..services.escopo import is_admin_escola, is_coordenador
    eh_admin = is_admin_escola(request.user) and not is_coordenador(request.user)
    if not eh_admin and request.user.id != user_id:
        messages.error(request, 'Você não tem permissão para editar este perfil.')
        return redirect('cal:home')

    usuario = get_object_or_404(User, id=user_id)
    # Captura papel anterior para detectar mudança
    papel_antes = None
    if eh_admin:
        try:
            papel_antes = usuario.perfil.papel
        except PerfilUsuario.DoesNotExist:
            papel_antes = None

    # Auto-edição: form simples; admin/superadmin (não coord): form completo
    if eh_admin:
        FormClass = UsuarioForm
        kwargs = {"instance": usuario, "request_user": request.user}
    else:
        FormClass = UsuarioUpdateForm
        kwargs = {"instance": usuario}

    if request.method == 'POST':
        form = FormClass(request.POST, **{k: v for k, v in kwargs.items() if k != "instance"}, instance=usuario)
        if form.is_valid():
            form.save()
            # Auditoria de mudança de papel
            if eh_admin:
                try:
                    papel_depois = usuario.perfil.papel
                except PerfilUsuario.DoesNotExist:
                    papel_depois = None
                if papel_antes != papel_depois:
                    registrar_auditoria(
                        request.user,
                        LogAuditoria.ACAO_MUDAR_PAPEL,
                        f"Alterou o papel de '{usuario.username}': "
                        f"{papel_antes or '—'} → {papel_depois or '—'}.",
                        recurso="User",
                        recurso_id=usuario.id,
                        escola=getattr(usuario.perfil, "escola", None) if hasattr(usuario, "perfil") else None,
                        detalhes={"papel_antes": papel_antes, "papel_depois": papel_depois},
                    )
            messages.success(request, 'Usuário atualizado com sucesso!')
            if eh_admin:
                return redirect('cal:listar_usuarios')
            return redirect('cal:perfil')
    else:
        form = FormClass(**kwargs)
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Editar Usuário'})


@login_required
def listar_usuarios(request):
    from ..services.escopo import (
        is_admin_escola, is_superadmin, is_coordenador, escolas_administradas,
        papel_de,
    )
    perfil_papel = papel_de(request.user)
    if not (is_admin_escola(request.user)):
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('cal:home')
    # Coordenador: somente leitura (sem botões de criar/editar/excluir)
    eh_coordenador = (perfil_papel == PerfilUsuario.PAPEL_COORDENADOR)
    usuarios = (
        User.objects
        .select_related('perfil', 'perfil__escola', 'perfil__professor_vinculado')
    )
    if not is_superadmin(request.user):
        escolas = escolas_administradas(request.user)
        # Apenas usuários cujo perfil está vinculado a uma escola administrada
        usuarios = usuarios.filter(
            perfil__escola__in=escolas
        ) | usuarios.filter(
            perfil__escolas_extras__in=escolas
        )
        usuarios = usuarios.distinct()
    usuarios = usuarios.order_by('username')
    return render(request, 'user/listar.html', {
        'usuarios': usuarios,
        'pode_admin': not eh_coordenador,
    })


def _bloquear_coordenador_escrita(request):
    from ..services.escopo import is_coordenador
    if is_coordenador(request.user):
        messages.error(request, 'Coordenador tem acesso somente leitura aos usuários.')
        return redirect('cal:listar_usuarios')
    return None


@login_required
def adicionar_usuario(request):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    bloqueio = _bloquear_coordenador_escrita(request)
    if bloqueio: return bloqueio
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request_user=request.user)
        if form.is_valid():
            novo_user = form.save()
            registrar_auditoria(
                request.user,
                LogAuditoria.ACAO_CRIAR_USUARIO,
                f"Criou o usuário '{novo_user.username}'.",
                recurso="User",
                recurso_id=novo_user.id,
                escola=getattr(novo_user.perfil, "escola", None) if hasattr(novo_user, "perfil") else None,
                detalhes={
                    "username": novo_user.username,
                    "papel": form.cleaned_data.get("papel"),
                },
            )
            messages.success(request, 'Usuário adicionado com sucesso!')
            return redirect('cal:listar_usuarios')
    else:
        form = UsuarioForm(request_user=request.user)
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Adicionar Usuário'})


@login_required
def excluir_usuario(request, user_id):
    from ..services.escopo import is_admin_escola, is_superadmin, escolas_administradas
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    bloqueio = _bloquear_coordenador_escrita(request)
    if bloqueio: return bloqueio
    if request.user.id == user_id:
        messages.error(request, 'Você não pode excluir sua própria conta!')
        return redirect('cal:listar_usuarios')

    usuario = get_object_or_404(User, id=user_id)

    # Verifica escopo: admin_escola só pode excluir usuários das suas escolas
    if not is_superadmin(request.user):
        escolas = set(escolas_administradas(request.user).values_list("id", flat=True))
        perfil = getattr(usuario, "perfil", None)
        escolas_alvo = set()
        if perfil:
            if perfil.escola_id:
                escolas_alvo.add(perfil.escola_id)
            escolas_alvo.update(perfil.escolas_extras.values_list("id", flat=True))
        if not escolas_alvo.intersection(escolas):
            messages.error(request, 'Esse usuário não pertence à(s) sua(s) escola(s).')
            return redirect('cal:listar_usuarios')

    if request.method == 'POST':
        username = usuario.username
        escola_obj = getattr(usuario.perfil, "escola", None) if hasattr(usuario, "perfil") else None
        usuario.delete()
        registrar_auditoria(
            request.user,
            LogAuditoria.ACAO_EXCLUIR_USUARIO,
            f"Excluiu o usuário '{username}'.",
            recurso="User",
            recurso_id=user_id,
            escola=escola_obj,
            detalhes={"username": username},
        )
        messages.success(request, 'Usuário excluído com sucesso!')
    return redirect('cal:listar_usuarios')


@login_required
def resetar_senha(request, user_id):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    bloqueio = _bloquear_coordenador_escrita(request)
    if bloqueio: return bloqueio
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UsuarioPasswordResetForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['nova_senha'])
            usuario.save()
            registrar_auditoria(
                request.user,
                LogAuditoria.ACAO_RESETAR_SENHA,
                f"Resetou a senha de '{usuario.username}'.",
                recurso="User",
                recurso_id=usuario.id,
                escola=getattr(usuario.perfil, "escola", None) if hasattr(usuario, "perfil") else None,
            )
            messages.success(request, 'Senha redefinida com sucesso!')
            return redirect('cal:listar_usuarios')
    else:
        form = UsuarioPasswordResetForm()
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Resetar Senha'})


@login_required
def desativar_usuario(request, user_id):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    bloqueio = _bloquear_coordenador_escrita(request)
    if bloqueio: return bloqueio
    if request.method != 'POST':
        messages.error(request, 'Ação inválida.')
        return redirect('cal:listar_usuarios')
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    registrar_auditoria(
        request.user,
        LogAuditoria.ACAO_DESATIVAR_USER,
        f"Desativou o usuário '{user.username}'.",
        recurso="User",
        recurso_id=user.id,
        escola=getattr(user.perfil, "escola", None) if hasattr(user, "perfil") else None,
    )
    messages.success(request, "Usuário desativado com sucesso.")
    return redirect('cal:listar_usuarios')


@login_required
def home(request):
    from datetime import date, timedelta
    from django.db.models import Count
    from ..models import Aula, AgendaEvento
    from ..services.escopo import (
        is_admin_escola, is_superadmin, is_professor, is_aluno, is_responsavel,
        professor_do_usuario, aulas_do_usuario, eventos_do_usuario,
        alunos_do_consumidor, turmas_do_aluno, escolas_administradas,
    )

    user = request.user
    hoje = date.today()
    fim_semana = hoje + timedelta(days=7)
    admin = is_admin_escola(user)
    super_admin = is_superadmin(user)
    professor = professor_do_usuario(user)

    ctx = {
        "is_admin": admin,
        "is_superadmin": super_admin,
        "professor": professor,
        "hoje": hoje,
    }

    # ─── Aluno / Responsável ────────────────────────────────────────────
    if is_aluno(user) or is_responsavel(user):
        alunos = list(alunos_do_consumidor(user).select_related("turma", "turma__escola"))
        turmas_ids = list(turmas_do_aluno(user).values_list("id", flat=True))
        proximos = list(
            AgendaEvento.objects.filter(turma_id__in=turmas_ids)
            .filter(inicio__date__gte=hoje, inicio__date__lte=fim_semana)
            .select_related("turma", "materia", "professor")
            .order_by("inicio")[:8]
        )
        atrasados = list(
            AgendaEvento.objects.filter(turma_id__in=turmas_ids, inicio__date__lt=hoje)
            .order_by("-inicio")[:5]
        )
        ctx.update({
            "papel": "aluno" if is_aluno(user) else "responsavel",
            "alunos": alunos,
            "proximos_eventos": proximos,
            "eventos_atrasados": atrasados,
            "stats": {
                "proximos": len(proximos),
                "alunos": len(alunos),
            },
        })
        return render(request, 'home.html', ctx)

    # ─── Professor / Admin / Coordenador ───────────────────────────────
    aulas_qs = aulas_do_usuario(user)
    aulas_hoje = list(
        aulas_qs.filter(data_aula=hoje)
        .select_related("turma", "turma__escola", "materia")
        .order_by("turma__nome_turma")[:6]
    )
    deveres_proximos = list(
        aulas_qs.filter(
            data_entrega__isnull=False,
            data_entrega__gte=hoje,
            data_entrega__lte=fim_semana,
        )
        .select_related("turma", "turma__escola", "materia")
        .order_by("data_entrega")[:6]
    )
    pendentes_chamada = list(
        aulas_qs.filter(data_aula__lte=hoje)
        .annotate(_n=Count("diario"))
        .filter(_n=0)
        .select_related("turma", "turma__escola", "materia")
        .order_by("-data_aula")[:6]
    )

    stats = {
        "aulas_hoje":       len(aulas_hoje),
        "deveres_semana":   len(deveres_proximos),
        "chamadas_pendentes": len(pendentes_chamada),
    }
    if admin:
        if super_admin:
            stats["total_eventos"] = AgendaEvento.objects.count()
            stats["total_aulas"]   = Aula.objects.count()
        else:
            escolas_ids = list(escolas_administradas(user).values_list('id', flat=True))
            stats["total_eventos"] = AgendaEvento.objects.filter(escola_id__in=escolas_ids).count()
            stats["total_aulas"]   = Aula.objects.filter(escola_id__in=escolas_ids).count()

    ctx.update({
        "papel": "admin" if admin else ("professor" if is_professor(user) else "outro"),
        "aulas_hoje": aulas_hoje,
        "deveres_proximos": deveres_proximos,
        "pendentes_chamada": pendentes_chamada,
        "stats": stats,
    })
    return render(request, 'home.html', ctx)


def contato(request):
    return render(request, 'contato.html')


def manual_publico(request):
    return render(request, 'manual_publico.html')


# ─── Auditoria ──────────────────────────────────────────────────────────────

@login_required
def auditoria_list(request):
    """Lista de logs de auditoria — visível somente ao super-administrador."""
    from ..services.escopo import is_superadmin
    if not is_superadmin(request.user):
        messages.error(request, "Esta área é restrita ao super-administrador.")
        return redirect('cal:home')
    logs = LogAuditoria.objects.select_related("autor", "escola").order_by("-criado_em")
    acao_filtro = request.GET.get("acao") or ""
    if acao_filtro:
        logs = logs.filter(acao=acao_filtro)
    logs = logs[:500]  # paginação simples: últimos 500
    return render(request, "auditoria/list.html", {
        "logs": logs,
        "acoes": LogAuditoria.ACAO_CHOICES,
        "acao_filtro": acao_filtro,
    })
