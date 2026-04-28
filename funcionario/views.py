from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from .forms import (
    FuncionarioCreationForm,
    LoginForm,
    OperadorAccessForm,
    SolicitanteManagementCreateForm,
    SolicitanteManagementUpdateForm,
)
from .models import Funcionario
from wpp.utils import OrdemServiceWpp

from io import TextIOWrapper
import csv

ordem_service = OrdemServiceWpp()


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not getattr(request.user, 'is_staff', False) and getattr(request.user, 'tipo_acesso', None) != Funcionario.ADMINISTRADOR:
            messages.error(request, 'Apenas administradores podem acessar esta funcionalidade.')
            return redirect('home_solicitante')

        return view_func(request, *args, **kwargs)

    return _wrapped_view

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
                    if user.area == 'predial':
                        return redirect('home_predial')
                    return redirect('home_solicitante')

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
            return redirect('login')
        else:
            form = FuncionarioCreationForm()
        return render(request, 'cadastro/acesso.html', {'form': form})


@login_required
@admin_required
def cadastrar_acesso_operador(request):
    operadores = Funcionario.objects.filter(tipo_acesso=Funcionario.OPERADOR).order_by('nome')

    if request.method == 'POST':
        form = OperadorAccessForm(request.POST)
        if form.is_valid():
            operador = form.save(commit=False)
            operador.tipo_acesso = Funcionario.OPERADOR
            operador.is_staff = False
            operador.is_superuser = False
            operador.save()
            messages.success(request, f'Acesso de operador criado para {operador.nome}.')
            return redirect('cadastrar_acesso_operador')
    else:
        form = OperadorAccessForm()

    context = {
        'form': form,
        'operadores': operadores,
    }
    return render(request, 'cadastro/acesso-operador.html', context)


@login_required
@admin_required
def gerenciar_funcionarios(request):
    funcionarios = Funcionario.objects.filter(tipo_acesso=Funcionario.SOLICITANTE).order_by('nome', 'matricula')
    edit_id = request.GET.get('edit')
    funcionario_em_edicao = None

    if edit_id:
        funcionario_em_edicao = funcionarios.filter(pk=edit_id).first()

    create_form = SolicitanteManagementCreateForm()
    update_form = (
        SolicitanteManagementUpdateForm(instance=funcionario_em_edicao)
        if funcionario_em_edicao
        else SolicitanteManagementUpdateForm()
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == 'create':
            create_form = SolicitanteManagementCreateForm(request.POST)
            if create_form.is_valid():
                funcionario = create_form.save(commit=False)
                funcionario.tipo_acesso = Funcionario.SOLICITANTE
                funcionario.area = None
                funcionario.is_staff = False
                funcionario.is_superuser = False
                funcionario.save()
                success_message = f'Solicitante {funcionario.nome} cadastrado com sucesso.'
                if is_ajax:
                    refreshed_funcionarios = Funcionario.objects.filter(tipo_acesso=Funcionario.SOLICITANTE).order_by('nome', 'matricula')
                    return JsonResponse(
                        {
                            'success': True,
                            'message': success_message,
                            'count': refreshed_funcionarios.count(),
                            'table_html': render_to_string(
                                'cadastro/partials/solicitantes_table.html',
                                {'funcionarios': refreshed_funcionarios},
                                request=request,
                            ),
                            'create_form_html': render_to_string(
                                'cadastro/partials/solicitante_create_fields.html',
                                {'create_form': SolicitanteManagementCreateForm()},
                                request=request,
                            ),
                        }
                    )
                messages.success(request, success_message)
                return redirect('gerenciar_funcionarios')
            if is_ajax:
                return JsonResponse(
                    {
                        'success': False,
                        'form_html': render_to_string(
                            'cadastro/partials/solicitante_create_fields.html',
                            {'create_form': create_form},
                            request=request,
                        ),
                    },
                    status=400,
                )
        elif action == 'update':
            funcionario_id = request.POST.get('funcionario_id')
            funcionario_em_edicao = funcionarios.filter(pk=funcionario_id).first()
            if not funcionario_em_edicao:
                messages.error(request, 'Solicitante nao encontrado para edicao.')
                return redirect('gerenciar_funcionarios')

            update_form = SolicitanteManagementUpdateForm(request.POST, instance=funcionario_em_edicao)
            if update_form.is_valid():
                funcionario = update_form.save()
                funcionario.area = None
                funcionario.save(update_fields=['matricula', 'nome', 'telefone', 'area'])
                success_message = f'Solicitante {funcionario.nome} atualizado com sucesso.'
                if is_ajax:
                    refreshed_funcionarios = Funcionario.objects.filter(tipo_acesso=Funcionario.SOLICITANTE).order_by('nome', 'matricula')
                    funcionario.refresh_from_db()
                    return JsonResponse(
                        {
                            'success': True,
                            'message': success_message,
                            'count': refreshed_funcionarios.count(),
                            'table_html': render_to_string(
                                'cadastro/partials/solicitantes_table.html',
                                {'funcionarios': refreshed_funcionarios},
                                request=request,
                            ),
                            'update_form_html': render_to_string(
                                'cadastro/partials/solicitante_update_fields.html',
                                {
                                    'update_form': SolicitanteManagementUpdateForm(instance=funcionario),
                                    'funcionario_em_edicao': funcionario,
                                },
                                request=request,
                            ),
                        }
                    )
                messages.success(request, success_message)
                return redirect('gerenciar_funcionarios')
            if is_ajax:
                return JsonResponse(
                    {
                        'success': False,
                        'form_html': render_to_string(
                            'cadastro/partials/solicitante_update_fields.html',
                            {
                                'update_form': update_form,
                                'funcionario_em_edicao': funcionario_em_edicao,
                            },
                            request=request,
                        ),
                    },
                    status=400,
                )
        elif action == 'toggle_status':
            funcionario_id = request.POST.get('funcionario_id')
            funcionario = funcionarios.filter(pk=funcionario_id).first()
            if not funcionario:
                messages.error(request, 'Solicitante nao encontrado.')
                return redirect('gerenciar_funcionarios')

            funcionario.is_active = not funcionario.is_active
            funcionario.save(update_fields=['is_active'])
            status_label = 'ativado' if funcionario.is_active else 'inativado'
            messages.success(request, f'Solicitante {funcionario.nome} {status_label} com sucesso.')
            return redirect('gerenciar_funcionarios')

    context = {
        'funcionarios': funcionarios,
        'create_form': create_form,
        'update_form': update_form,
        'funcionario_em_edicao': funcionario_em_edicao,
    }
    return render(request, 'cadastro/funcionarios.html', context)

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

