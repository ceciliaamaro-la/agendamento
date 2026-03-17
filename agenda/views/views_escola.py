from django.shortcuts import render, get_object_or_404, redirect
from agenda.models import Escola
from agenda.forms import EscolaForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


@login_required
def escola_list(request):
    escolas = Escola.objects.all()
    return render(request, 'cal/escola_list.html', {'escolas': escolas})


@login_required
def escola_nova(request):
    if request.method == 'POST':
        form = EscolaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escola criada com sucesso!')
            return redirect('cal:escola_list')
    else:
        form = EscolaForm()
    return render(request, 'cal/escola_form.html', {'form': form})


@login_required
def escola_update(request, pk):
    escola = get_object_or_404(Escola, pk=pk)
    if request.method == 'POST':
        form = EscolaForm(request.POST, instance=escola)
        if form.is_valid():
            form.save()
            messages.success(request, 'Escola atualizada com sucesso!')
            return redirect('cal:escola_list')
    else:
        form = EscolaForm(instance=escola)
    return render(request, 'cal/escola_form.html', {'form': form})


@login_required
def escola_delete(request, pk):
    escola = get_object_or_404(Escola, pk=pk)
    if request.method == 'POST':
        escola.delete()
        messages.success(request, 'Escola excluída com sucesso!')
        return redirect('cal:escola_list')
    return render(request, 'cal/escola_confirm_delete.html', {'escola': escola})
