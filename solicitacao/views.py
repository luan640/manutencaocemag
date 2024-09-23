from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.core.serializers import serialize

from .forms import SolicitacaoForm, FotoForm, SolicitacaoPredialForm
from .models import Foto, Solicitacao
from cadastro.models import Maquina, Setor, Operador, TipoTarefas
from execucao.models import Execucao

import json

User = get_user_model()

@login_required
def criar_solicitacao(request):

    maquinas_producao = Maquina.objects.filter(area='producao')

    if request.method == 'POST':
    
        form = SolicitacaoForm(request.POST)
        form2 = FotoForm(request.POST, request.FILES)

        if form.is_valid() and form2.is_valid():

            solicitacao = form.save(commit=False)
            
            if isinstance(request.user, User):
                solicitacao.solicitante = request.user
                solicitacao.area = 'producao'
                solicitacao.save()

                for imagem in request.FILES.getlist('imagens'):
                    Foto.objects.create(solicitacao=solicitacao, imagem=imagem)

                if 'video' in request.FILES:
                    solicitacao.video = request.FILES['video']
                    solicitacao.save()
                
                # Adiciona uma mensagem de sucesso
                messages.success(request, 'Solicitação enviada com sucesso!')
                
                # Redireciona para a página de sucesso
                return redirect(reverse('solicitacao_sucesso', kwargs={'area': 'producao'}))

            else:
                return render(request, 'erro.html', {'mensagem': 'Usuário inválido.'})
        else:
            print(form.errors)
            print(form2.errors) 
    else:
        form = SolicitacaoForm()
        form2 = FotoForm()

    return render(request, 'solicitacao/solicitacao.html', {
        'form': form,
        'form2': form2,
        'maquinas_producao':maquinas_producao,

    })

@login_required
def criar_solicitacao_predial(request):
    maquinas_predial = Maquina.objects.filter(area='predial')

    if request.method == 'POST':
        form = SolicitacaoPredialForm(request.POST)
        form2 = FotoForm(request.POST, request.FILES)

        if form.is_valid() and form2.is_valid():
            solicitacao = form.save(commit=False)
            
            if isinstance(request.user, User):
                solicitacao.solicitante = request.user
                solicitacao.area = 'predial'
                solicitacao.save()

                for imagem in request.FILES.getlist('imagens'):
                    Foto.objects.create(solicitacao=solicitacao, imagem=imagem)

                # Adiciona uma mensagem de sucesso
                messages.success(request, 'Solicitação enviada com sucesso!')

                # Redireciona para a página de sucesso
                return redirect(reverse('solicitacao_sucesso', kwargs={'area': 'predial'}))

            else:
                return render(request, 'erro.html', {'mensagem': 'Usuário inválido.'})
        else:
            print(form.errors)
            print(form2.errors)
    else:
        form = SolicitacaoForm()
        form2 = FotoForm()

    return render(request, 'solicitacao/solicitacao-predial.html', {
        'form': form,
        'form2': form2,
        'maquinas_predial': maquinas_predial
    })

def solicitacao_sucesso(request, area):
    return render(request, 'solicitacao/sucesso.html', {'area':area})

@csrf_exempt
def atualizar_status_maq_parada(request):
    
    if request.method == 'POST':
        data = json.loads(request.body)
        solicitacao_id = data.get('solicitacao_id')
        maq_parada = data.get('maq_parada')

        try:
            solicitacao = Solicitacao.objects.get(id=solicitacao_id)
            solicitacao.maq_parada = maq_parada
            solicitacao.save()
            return JsonResponse({'success': True})
        except Solicitacao.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Solicitação não encontrada.'})
    return JsonResponse({'success': False, 'error': 'Método não permitido.'})

def filtrar_maquinas_por_setor(request):
    setor_id = request.GET.get('setor_id')
    area = request.GET.get('tipo_solicitacao')

    if setor_id:
        maquinas = Maquina.objects.filter(setor_id=setor_id, area=area)  # Filtra as máquinas pelo setor selecionado
        maquinas_data = list(maquinas.values('id', 'codigo', 'descricao'))  # Converte as máquinas para um formato simples de lista
    else:
        maquinas_data = []

    return JsonResponse({'maquinas': maquinas_data})

@login_required
def tarefa_rotina(request):
    maquinas = Maquina.objects.filter(area='predial')
    setores = Setor.objects.all()
    operadores = Operador.objects.filter(area='predial')
    tipo_tarefas = TipoTarefas.objects.all()

    if request.method == 'POST':
        id_setor = request.POST.get('setor')
        id_maquina = request.POST.get('maquina')
        id_tarefa = request.POST.get('tarefa')
        descricao_tarefa = request.POST.get('descricao_tarefa')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        operadores_ids = request.POST.getlist('operador')  # Usar getlist para campos ManyToMany
        status = request.POST.get('status')

        # Validar o setor, máquina, operador, tarefa, etc.
        setor = Setor.objects.get(id=id_setor)
        maquina = Maquina.objects.get(id=id_maquina)
        tarefa = TipoTarefas.objects.get(id=id_tarefa)

        # Criar o objeto Tarefa (ou outro modelo que esteja sendo usado)
        nova_solicitacao = Solicitacao.objects.create(
            setor=setor,
            maquina=maquina,
            solicitante=request.user,
            descricao=descricao_tarefa,
            area='predial',
            tarefa=tarefa,
        )

        nova_execucao = Execucao.objects.create(
            ordem=nova_solicitacao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status,
        )

        nova_execucao.operador.set(operadores_ids)  # Usar o .set() para ManyToMany

        messages.success(request, "Solicitação de tarefa criada com sucesso!")
        return redirect('tarefa_rotina')  # Redireciona para a mesma página ou outra desejada

    context = {
        'maquinas': maquinas,
        'setores': setores,
        'operadores': operadores,
        'tipo_tarefas': tipo_tarefas
    }

    return render(request, 'tarefa-rotina/solicitacao-tarefa.html', context)

def get_maquina_by_setor(request):
    setor = request.GET.get('setor')

    # Filtrar as máquinas pelo setor
    maquinas = Maquina.objects.filter(setor=setor)

    if maquinas.exists():
        # Serializar os dados das máquinas para JSON
        maquinas_serializadas = serialize('json', maquinas)

        return JsonResponse({'maquinas': maquinas_serializadas}, safe=False)
    
    # Retornar erro caso não haja máquinas encontradas
    return JsonResponse({'error': 'Setor não encontrado'}, status=404)

def get_maquina_by_eq_em_falha(request):
    setor = request.GET.get('setor')
    tipo = request.GET.get('tipo')
    print(tipo)

    # Filtrar as máquinas pelo setor
    maquinas = Maquina.objects.filter(setor=setor,tipo=tipo)

    if maquinas.exists():
        # Serializar os dados das máquinas para JSON
        maquinas_serializadas = serialize('json', maquinas)

        return JsonResponse({'maquinas': maquinas_serializadas}, safe=False)
    
    # Retornar erro caso não haja máquinas encontradas
    return JsonResponse({'error': 'Setor não encontrado'}, status=404)
