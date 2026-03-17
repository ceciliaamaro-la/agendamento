# cal/views/views_login.py

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from agenda.forms import UserRegisterForm
import logging



logger = logging.getLogger('django')



def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Criar categorias padrão para o novo usuário
            categorias_padrao = [
                'Alimentação', 'Transporte', 'Moradia', 'Lazer', 
                'Saúde', 'Educação', 'Salário', 'Investimentos',
                'Outros'
            ]
            
            
            login(request, user)  # login automático após cadastro
            messages.success(request, 'Cadastro realizado com sucesso!')
            logger.info(f'Novo usuário registrado: {user.username}')
            return redirect('cal:home')  # ou outra página
    else:
        form = UserRegisterForm()
    return render(request, 'registration/register.html', {'form': form})

from django.contrib.auth import authenticate, login as login_django
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import logout

def login_view(request):  # ✅ Evite sobrescrever 'login'
    if request.method == "GET":
        
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:
            login_django(request, user)
            return redirect('cal:home')
        else:
            messages.error(request, 'Usuário ou senha inválidos. Por favor, tente novamente.')
            return redirect('login')

from django.contrib.auth.views import LogoutView

class CustomLogoutView(LogoutView):
    next_page = '/bemvindo/'
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)
