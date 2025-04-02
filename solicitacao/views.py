from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.core.serializers import serialize
from django.db import transaction
from django.core.files.base import ContentFile
from django.db import IntegrityError

from .utils import criar_solicitacoes_aleatorias
from .forms import SolicitacaoForm, FotoForm, SolicitacaoPredialForm
from .models import Foto, Solicitacao
from cadastro.models import Maquina, Setor, Operador, TipoTarefas
from execucao.models import Execucao, MaquinaParada
from preventiva.models import PlanoPreventiva

import json
import requests

User = get_user_model()

@login_required
def criar_solicitacao(request):
    maquinas_producao = Maquina.objects.filter(area='producao')

    if request.method == 'POST':
        form = SolicitacaoForm(request.POST)
        form2 = FotoForm(request.POST, request.FILES)

        if form.is_valid() and form2.is_valid():
            try:
                with transaction.atomic():
                    solicitacao = form.save(commit=False)
                    
                    # Associa o usuário solicitante e define a área
                    solicitacao.solicitante = request.user
                    solicitacao.area = 'producao'
                    solicitacao.save()

                    # Salvamento das imagens associadas à solicitação
                    for imagem in request.FILES.getlist('imagens'):
                        Foto.objects.create(solicitacao=solicitacao, imagem=imagem)

                    # Salvamento do vídeo, se fornecido
                    if 'video' in request.FILES:
                        solicitacao.video = request.FILES['video']
                        solicitacao.save()

                    # Adiciona mensagem de sucesso e redireciona
                    return redirect(reverse('solicitacao_sucesso', kwargs={'area': 'producao', 'rotina':False}))

            except Exception as e:
                # Captura erros durante a transação
                messages.error(request, f'Erro ao enviar solicitação: {e}')
        else:
            # Exibe as mensagens de erro
            messages.error(request, 'Há erros no formulário. Por favor, corrija-os.')
            print(form.errors)
            print(form2.errors)
    else:
        form = SolicitacaoForm()
        form2 = FotoForm()

    return render(request, 'solicitacao/solicitacao.html', {
        'form': form,
        'form2': form2,
        'maquinas_producao': maquinas_producao,
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

                # Redireciona para a página de sucesso
                return redirect(reverse('solicitacao_sucesso', kwargs={'area':'predial', 'rotina':False}))

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

@login_required
def criar_execucao_rotina(request):
    # maquinas_predial = Maquina.objects.filter(area='predial')
    operadores = Operador.objects.filter(area='predial')
    tipo_tarefas = TipoTarefas.objects.filter(status=True)

    if request.method == 'POST':

        operadores_ids = request.POST.getlist('operador')  # Usar getlist para campos ManyToMany
        observacao = request.POST.get('obs')
        
        data_inicio = request.POST.get('data_inicio')
        if 'T' in data_inicio:
            data_programacao = data_inicio.split('T')[0]
        data_fim = request.POST.get('data_fim')

        tarefa_rotina = request.POST.get('tarefa_rotina')
        tarefa = get_object_or_404(TipoTarefas, pk=tarefa_rotina)

        with transaction.atomic():
            
            if isinstance(request.user, User):
                
                solicitacao = Solicitacao.objects.create(
                    solicitante = request.user,
                    area = 'predial',
                    impacto_producao = 'baixo',
                    descricao = 'Tarefa de rotina',
                    status = 'aprovar',
                    status_andamento = 'finalizada',
                    programacao = data_programacao,
                    tarefa = tarefa,
                    setor = get_object_or_404(Setor, pk=2), # Setor "administrativo"
                    maquina = get_object_or_404(Maquina, pk=190) # Máquina "outro"
                )
                solicitacao.data_abertura = data_inicio
                solicitacao.save()

                execucao = Execucao.objects.create(
                    ordem=solicitacao,
                    n_execucao=0,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    observacao=observacao,
                    status='finalizada',
                )
                
                execucao.operador.set(operadores_ids)  # Usar o .set() para ManyToMany
                execucao.save()

                # Redireciona para a página de sucesso
                return redirect(reverse('solicitacao_sucesso', kwargs={'area': 'predial', 'rotina': True}))

            else:
                return render(request, 'erro.html', {'mensagem': 'Usuário inválido.'})

    return render(request, 'execucao/executar-tarefa-rotina.html', {
        'tarefas': tipo_tarefas,
        'operadores': operadores
    })

def solicitacao_sucesso(request, area, rotina):
    return render(request, 'solicitacao/sucesso.html', {'area':area,'rotina':rotina})

@csrf_exempt
def atualizar_status_maq_parada(request):
    
    if request.method == 'POST':
        data = json.loads(request.body)
        solicitacao_id = data.get('solicitacao_id')
        cod_maq_json = data.get('cod_maquina')
        
        # maq_parada = data.get('maq_parada')

        try:

            solicitacao = Solicitacao.objects.get(id=solicitacao_id)
            if cod_maq_json:
                codigo_maquina = cod_maq_json
            else:
                if solicitacao.maquina == '' or solicitacao.maquina is None:
                    print('Lidando com uma Ferramenta')
                    return JsonResponse({'success': True,
                                    'parada': False})
                codigo_maquina = solicitacao.maquina.id
            maquina_parada = MaquinaParada.objects.filter(ordem__maquina__id=codigo_maquina, data_fim__isnull=True)

            # Verifica se a solicitação que está pra ser executada é a que deixou a máquina parada
            solicitacao_inicial_maquina_parada = False
            if maquina_parada.filter(ordem=solicitacao).exists():
                print('Solicitação que será executada é da máquina que está parada!')
                solicitacao_inicial_maquina_parada = True

            # print("Quantidade ordens:",len(maquina_parada))
            if maquina_parada and not solicitacao_inicial_maquina_parada:
                print("Esta máquina já está parada!")
                return JsonResponse({'success': True,
                                     'parada' : True})
            else:
                print("Máquina funcionando")
                return JsonResponse({'success': True,
                                    'parada': False})
            # print(execucoes)
            # for execucao in execucoes:
            #     print(execucao.ordem.maquina.codigo)
            #     print(execucao.ordem.descricao)
            # solicitacao.maq_parada = maq_parada
            # solicitacao.save()

            
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

def get_maquina_by_setor(request):
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Filtrar as máquinas pelo setor
    maquinas = Maquina.objects.filter(setor=setor, area=area)

    if maquinas.exists():
        # Serializar os dados das máquinas para JSON
        maquinas_serializadas = serialize('json', maquinas)

        return JsonResponse({'maquinas': maquinas_serializadas}, safe=False)
    
    # Retornar erro caso não haja máquinas encontradas
    return JsonResponse({'error': 'Setor não encontrado'}, status=404)

def get_maquina_by_eq_em_falha(request):
    setor = request.GET.get('setor')
    tipo = request.GET.get('tipo')

    # Filtrar as máquinas pelo setor
    maquinas = Maquina.objects.filter(setor=setor,tipo=tipo)

    if maquinas.exists():
        # Serializar os dados das máquinas para JSON
        maquinas_serializadas = serialize('json', maquinas)

        return JsonResponse({'maquinas': maquinas_serializadas}, safe=False)
    
    # Retornar erro caso não haja máquinas encontradas
    return JsonResponse({'error': 'Setor não encontrado'}, status=404)

def get_maquinas(request):
    maquinas = Maquina.objects.filter(area='producao').values('id', 'codigo','descricao')
    if maquinas.exists():
        maquinas_serializadas = [{'id': maquina['id'], 'text': maquina['codigo'] + " - " + maquina['descricao'] if maquina['descricao'] else maquina['codigo']} for maquina in maquinas]
        return JsonResponse({'results': maquinas_serializadas}, safe=False)
    return JsonResponse({'error': 'Nenhuma máquina encontrada'}, status=404)

def get_maquinas_setor(request, setor_id):
    maquinas = Maquina.objects.filter(area='producao',setor__id=setor_id).values('id', 'codigo','descricao')
    if maquinas.exists():
        maquinas_serializadas = [{'id': maquina['id'], 'text': maquina['codigo'] + " - " + maquina['descricao'] if maquina['descricao'] else maquina['codigo']} for maquina in maquinas]
        return JsonResponse({'results': maquinas_serializadas}, safe=False)
    return JsonResponse({'error': 'Nenhuma máquina encontrada'}, status=404)

def get_setores(request):

    setores = Setor.objects.all().values('id', 'nome')
    if setores.exists():
        setores_serializadas = [{'id': setor['id'], 'text': setor['nome']} for setor in setores]
        return JsonResponse({'results': setores_serializadas}, safe=False)
    return JsonResponse({'error': 'Nenhum setor encontrado'}, status=404)

def pagina_satisfacao(request, ordem_id):
    # Buscar a ordem pelo ID
    ordem = get_object_or_404(Solicitacao, pk=ordem_id)

    # Verificar se a satisfação já foi registrada
    if ordem.satisfacao_registrada:
        # Se já foi registrada, mostrar mensagem de "Ordem já foi finalizada"
        return render(request, 'solicitacao/sucesso.html', {'mensagem': 'Ordem já finalizada.',})
    
    # Passando o ID da ordem para o template se ainda não foi registrada
    context = {'ordem_id': ordem_id}
    return render(request, 'solicitacao/satisfacao.html', context)

def processar_satisfacao(request, ordem_id):
    # Buscar a ordem pelo ID
    ordem = get_object_or_404(Solicitacao, pk=ordem_id)

    # Verificar se a satisfação já foi registrada
    if ordem.satisfacao_registrada:
        # Se já foi registrada, mostrar mensagem de "Ordem já foi finalizada"
        return render(request, 'solicitacao/sucesso.html', {'mensagem': 'Ordem já finalizada.'})

    # Obtendo a resposta do usuário
    resposta = request.POST.get('resposta')

    # Processar a resposta conforme necessário
    if resposta in ['sim', 'nao']:
        with transaction.atomic():
            
            # Atualizar a ordem para indicar que a satisfação foi registrada
            ordem.satisfacao_registrada = True
            ordem.save()

            # Lógica para salvar a resposta e fazer outras ações
            if resposta == 'sim':
                print(f"Ordem {ordem_id}: Usuário respondeu Sim.")
            else:
                # Se a resposta for "Não", abrir uma nova solicitação com as mesmas informações
                nova_ordem = Solicitacao.objects.create(
                    setor=ordem.setor,
                    maquina=ordem.maquina,
                    maq_parada=ordem.maq_parada,
                    solicitante=ordem.solicitante,
                    equipamento_em_falha=ordem.equipamento_em_falha,
                    setor_maq_solda=ordem.setor_maq_solda,
                    impacto_producao=ordem.impacto_producao,
                    tipo_ferramenta=ordem.tipo_ferramenta,
                    codigo_ferramenta=ordem.codigo_ferramenta,
                    video=ordem.video,
                    descricao=f"Solicitante optou por reabrir a ordem #OS{ordem_id}.\nMotivo anterior: " + ordem.descricao + '\nOrdem aberta novamente de forma automática.',
                    area=ordem.area,
                    planejada=ordem.planejada,
                    prioridade=ordem.prioridade,
                    tarefa=ordem.tarefa,
                    comentario_manutencao=ordem.comentario_manutencao,
                    status=ordem.status,
                    satisfacao_registrada=False  # Definir como não registrada para a nova solicitação
                )

                # Copiar as imagens associadas à solicitação original
                for foto in ordem.fotos.all():
                    response = requests.get(foto.imagem.url)
                    if response.status_code == 200:
                        nova_foto = Foto.objects.create(
                            solicitacao=nova_ordem,
                        )
                        nova_foto.imagem.save(foto.imagem.name, ContentFile(response.content), save=True)

                print(f"Ordem {ordem_id}: Usuário respondeu Não. Nova solicitação criada com ID {nova_ordem.pk}.")

        return render(request, 'solicitacao/sucesso.html', {'mensagem': 'Ordem finalizada com sucesso!'})

def get_planos_preventiva(request, maquina_id):
    planos = PlanoPreventiva.objects.filter(maquina_id=maquina_id).values('id', 'nome')

    return JsonResponse(list(planos), safe=False)

@login_required
def gerar_solicitacoes(request, qtd=10):
    """
    View para gerar 'qtd' solicitações aleatórias.
    """
    try:
        criar_solicitacoes_aleatorias(qtd)  # Chama a função utilitária
        return JsonResponse({'success': f'{qtd} solicitações geradas com sucesso.'}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def criar_tarefa_rotina(request):
    
    try:
        data = json.loads(request.body)
    except:
        pass

    if request.method == 'POST':
        nome_tarefa = request.POST.get('nome_tarefa')

        if nome_tarefa:
            try:
                # Salva a nova tarefa no banco de dados
                TipoTarefas.objects.create(nome=nome_tarefa)

                # Retorna uma resposta JSON indicando sucesso
                return JsonResponse({'status': 'success', 'message': 'Tarefa criada com sucesso!'})
            
            except IntegrityError:
                return JsonResponse({'status': 'error', 'message': 'Tarefa já existe!'})
        elif data:

            nome_tarefa = data.get('nome_tarefa')
            type_status = data.get('type_status')

            tipo_tarefa_object = get_object_or_404(TipoTarefas, nome=nome_tarefa)
            tipo_tarefa_object.status = type_status
            tipo_tarefa_object.save()

            if type_status:
                return JsonResponse({'status':'success', 'message':'Tarefa habilitada com sucesso'})
            else:
                return JsonResponse({'status':'success', 'message':'Tarefa desabilitada com sucesso'})

        # Retorna uma resposta JSON indicando falha
        return JsonResponse({'status': 'error', 'message': 'O nome da tarefa é obrigatório!'})
        
    tarefas_existentes = TipoTarefas.objects.all()

    return render(request, "tarefa-rotina/add-tarefa.html", {"tarefas_existentes":tarefas_existentes}) 

# def obter_choices(request):
#     # Pegando as opções do campo 'meu_atributo'
#     form = SolicitacaoForm()

#     # O campo 'meu_atributo' é um ChoiceField, então podemos pegar as opções
#     equipamento_em_falha = form.fields['equipamento_em_falha'].choices
#     setor_maq_solda = form.fields['setor_maq_solda'].choices
#     tipo_ferramenta = form.fields['tipo_ferramenta'].choices

#     print(equipamento_em_falha)
#     print(setor_maq_solda)
#     print(tipo_ferramenta)
    
#     # Retornamos essas opções como um JSON
#     return JsonResponse({'equipamento_em_falha': equipamento_em_falha,
#                          'setor_maq_solda': setor_maq_solda,
#                          'tipo_ferramenta': tipo_ferramenta})
