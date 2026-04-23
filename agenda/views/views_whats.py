from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def _desativado(request):
    messages.warning(request, 'O envio por WhatsApp foi desativado neste sistema.')
    return redirect('cal:home')


@login_required
def whats_list(request):
    return _desativado(request)


@login_required
def whats_create(request):
    return _desativado(request)


@login_required
def whats_update(request, pk):
    return _desativado(request)


@login_required
def whats_delete(request, pk):
    return _desativado(request)
