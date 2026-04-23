from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from ..forms import UsuarioForm, UsuarioUpdateForm, UsuarioPasswordResetForm
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
    if request.method == 'POST':
        if 'perfil_submit' in request.POST:
            form = UsuarioUpdateForm(request.POST, instance=request.user)
            password_form = PasswordChangeForm(request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Perfil atualizado com sucesso!')
                return redirect('cal:perfil')
        elif 'password_submit' in request.POST:
            form = UsuarioUpdateForm(instance=request.user)
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso!')
                return redirect('cal:perfil')
    else:
        form = UsuarioUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'user/form_usuario.html', {
        'form': form,
        'password_form': password_form,
        'titulo': 'Meu Perfil'
    })


@login_required
def editar_usuario(request, user_id):
    if not request.user.is_staff and request.user.id != user_id:
        messages.error(request, 'Você não tem permissão para editar este perfil.')
        return redirect('cal:home')

    usuario = get_object_or_404(User, id=user_id)
    # Auto-edição: usa form simples; admin/staff: usa form completo (User+Perfil)
    if request.user.is_staff or request.user.is_superuser:
        FormClass = UsuarioForm
        kwargs = {"instance": usuario, "request_user": request.user}
    else:
        FormClass = UsuarioUpdateForm
        kwargs = {"instance": usuario}

    if request.method == 'POST':
        form = FormClass(request.POST, **{k: v for k, v in kwargs.items() if k != "instance"}, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso!')
            if request.user.is_staff:
                return redirect('cal:listar_usuarios')
            return redirect('cal:perfil')
    else:
        form = FormClass(**kwargs)
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Editar Usuário'})


@login_required
def listar_usuarios(request):
    from ..services.escopo import (
        is_admin_escola, is_superadmin, escolas_administradas,
    )
    if not is_admin_escola(request.user):
        messages.error(request, 'Você não tem permissão para acessar esta página.')
        return redirect('cal:home')
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
    return render(request, 'user/listar.html', {'usuarios': usuarios})


@login_required
def adicionar_usuario(request):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário adicionado com sucesso!')
            return redirect('cal:listar_usuarios')
    else:
        form = UsuarioForm(request_user=request.user)
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Adicionar Usuário'})


@login_required
def excluir_usuario(request, user_id):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    if request.user.id == user_id:
        messages.error(request, 'Você não pode excluir sua própria conta!')
        return redirect('cal:listar_usuarios')

    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        usuario.delete()
        messages.success(request, 'Usuário excluído com sucesso!')
    return redirect('cal:listar_usuarios')


@login_required
def resetar_senha(request, user_id):
    from ..services.escopo import is_admin_escola
    if not is_admin_escola(request.user):
        messages.error(request, 'Sem permissão.')
        return redirect('cal:home')
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UsuarioPasswordResetForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['nova_senha'])
            usuario.save()
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
    if request.method != 'POST':
        messages.error(request, 'Ação inválida.')
        return redirect('cal:listar_usuarios')
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, "Usuário desativado com sucesso.")
    return redirect('cal:listar_usuarios')


@login_required
def home(request):
    from datetime import date, timedelta
    from django.db.models import Count
    from ..models import Aula, AgendaEvento
    from ..services.escopo import (
        is_admin_escola, is_superadmin, professor_do_usuario,
        aulas_do_usuario, escolas_administradas,
    )

    user = request.user
    hoje = date.today()
    fim_semana = hoje + timedelta(days=7)
    admin = is_admin_escola(user)
    super_admin = is_superadmin(user)
    professor = professor_do_usuario(user)

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

    # Aulas com data já passada (ou hoje) sem nenhum registro de chamada
    pendentes_chamada = list(
        aulas_qs.filter(data_aula__lte=hoje)
        .annotate(_n=Count("diario"))
        .filter(_n=0)
        .select_related("turma", "turma__escola", "materia")
        .order_by("-data_aula")[:6]
    )

    # Estatísticas para os cards
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

    return render(request, 'home.html', {
        "is_admin": admin,
        "is_superadmin": super_admin,
        "professor": professor,
        "aulas_hoje": aulas_hoje,
        "deveres_proximos": deveres_proximos,
        "pendentes_chamada": pendentes_chamada,
        "stats": stats,
        "hoje": hoje,
    })


def contato(request):
    return render(request, 'contato.html')


def manual_publico(request):
    return render(request, 'manual_publico.html')
