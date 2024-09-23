from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm, CadastroUsuarioForm

def login_view(request):
    form = LoginForm(request.POST or None)
    if form.is_valid():
        user = form.get_user()
        if user:
            login(request, user)
            user = request.user

            if user.is_administrador():
                if user.area == 'producao':
                    return redirect('home_producao')
                elif user.area == 'predial':
                    return redirect('home_predial')
            else:
                return redirect('home_solicitante')
    else:
        print(form.errors)
        
    return render(request, 'login/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def cadastrar_usuario(request):
    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redireciona para a página de login após o cadastro
    else:
        form = CadastroUsuarioForm()
    
    return render(request, 'cadastro/acesso.html', {'form': form})

