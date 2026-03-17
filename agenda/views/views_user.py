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
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso!')
            if request.user.is_staff:
                return redirect('cal:listar_usuarios')
            return redirect('cal:perfil')
    else:
        form = UsuarioUpdateForm(instance=usuario)
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Editar Usuário'})


@login_required
@staff_member_required
def listar_usuarios(request):
    usuarios = User.objects.all().order_by('username')
    return render(request, 'user/listar.html', {'usuarios': usuarios})


@login_required
@staff_member_required
def adicionar_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário adicionado com sucesso!')
            return redirect('cal:listar_usuarios')
    else:
        form = UsuarioForm()
    return render(request, 'user/form_usuario.html', {'form': form, 'titulo': 'Adicionar Usuário'})


@login_required
@staff_member_required
def excluir_usuario(request, user_id):
    if request.user.id == user_id:
        messages.error(request, 'Você não pode excluir sua própria conta!')
        return redirect('cal:listar_usuarios')

    if request.method == 'POST':
        usuario = get_object_or_404(User, id=user_id)
        usuario.delete()
        messages.success(request, 'Usuário excluído com sucesso!')
    return redirect('cal:listar_usuarios')


@login_required
@staff_member_required
def resetar_senha(request, user_id):
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
@staff_member_required
def desativar_usuario(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, "Usuário desativado com sucesso.")
    return redirect('cal:listar_usuarios')


def home(request):
    return render(request, 'home.html', {})


def contato(request):
    return render(request, 'contato.html')


def manual_publico(request):
    return render(request, 'manual_publico.html')
