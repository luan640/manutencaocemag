from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import FuncionarioCreationForm, LoginForm#, CadastroUsuarioForm, 
from wpp.utils import OrdemServiceWpp

from io import TextIOWrapper
import csv

ordem_service = OrdemServiceWpp()

def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            if user:
                login(request, user)  # Realiza o login
                print(f"Usuário {user.matricula} autenticado com sucesso.")

                # Redireciona com base no tipo de usuário
                if user.is_administrador():
                    if user.area == 'producao':
                        return redirect('home_producao')
                    elif user.area == 'predial':
                        return redirect('home_predial')
                else:
                    return redirect('home_solicitante')
        else:
            print(form.errors)  # Depuração para verificar erros no formulário

    return render(request, 'login/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def cadastrar_usuario(request):
    if request.method == 'POST':
        form = FuncionarioCreationForm(request.POST)
        if form.is_valid():
            form.save()
            redirect('login')
            # Redirecionar ou retornar uma resposta
        else:
            form = FuncionarioCreationForm()
        return render(request, 'cadastro/acesso.html', {'form': form})

@login_required
def cadastrar_usuarios_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = TextIOWrapper(request.FILES['csv_file'].file, encoding='utf-8')
        reader = csv.DictReader(csv_file)
        
        errors = []
        for row in reader:
            form = FuncionarioCreationForm({
                'matricula': row['matricula'],
                'nome': row['nome'],
                'tipo_acesso': row['tipo_acesso'],
                'area': row['area'],
                'telefone': row['telefone'],
                'password1': row['password1'],
                'password2': row['password2'],  # Valida ambas as senhas para cada usuário
            })
            if form.is_valid():
                form.save()
            else:
                errors.append(f"Erro ao processar a matrícula {row['matricula']}: {form.errors}")
        
        if errors:
            return render(request, 'cadastro/cadastrar-usuario-csv.html', {'errors': errors})
        return redirect('login')  # Redireciona após o cadastro
    return render(request, 'cadastro/cadastrar-usuario-csv.html')

def primeiro_acesso(request):
    if request.method == 'POST':
        print(request.POST)
        form = FuncionarioCreationForm(request.POST)
        form.tipo_acesso = 'solicitante'

        if form.is_valid():

            form.save()

            kwargs = {
                'login':request.POST.get('matricula'),
                'password':request.POST.get('password2')
            }

            # enviar wpp informando a senha e login
            status_code, response_data = ordem_service.sucesso_criar_conta(request.POST.get('telefone'), kwargs)
            print(status_code, response_data)

            return redirect('login')
    else:
        form = FuncionarioCreationForm()
    return render(request, 'cadastro/primeiro-acesso.html', {'form': form})

