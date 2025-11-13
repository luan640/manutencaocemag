from django.shortcuts import render, get_object_or_404
from django.db.models import OuterRef, Subquery, Value, Q, Count, F
from django.db.models.functions import Concat
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.timezone import now, is_naive, make_naive, make_aware
from django.urls import reverse
from django.db import transaction
from django.utils.dateparse import parse_datetime

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao
from cadastro.models import Setor, Operador
from wpp.utils import OrdemServiceWpp
from home.utils import buscar_telefone
from dashboard.views import quantidade_atrasada

from .utils import *

import json

ordem_service = OrdemServiceWpp()

@login_required
def home_producao(request):
    # Definir filtros iniciais
    base_filters = (Q(status__isnull=True) | Q(status='aprovar')) & Q(area='producao')
    
    # Filtrar por solicitante se o usuário for um 'solicitante'
    if request.user.tipo_acesso == 'solicitante':
        base_filters &= Q(solicitante=request.user)
        filtros={'solicitante_id':request.user.id, 'area':'producao'}
    else:
        filtros={'area':'producao'}
    # Obter as solicitações com base nos filtros
    solicitacoes = Solicitacao.objects.filter(base_filters)

    # Anotar contagens de status_andamento
    status_counts = solicitacoes.values('status_andamento').annotate(count=Count('id'))

    # Converter para um dicionário para acesso rápido
    status_counts_dict = {item['status_andamento']: item['count'] for item in status_counts}

    # Mapeamento dos nomes das variáveis para os status
    status_variables = {
        'quantidade_em_aberto': 'em_espera',
        'quantidade_finalizada': 'finalizada',
        'quantidade_em_execucao': 'em_execucao',
        'aguardando_material': 'aguardando_material',
        'aguardando_primeiro_atendimento_card': 'aguardando_atendimento',
    }

    # Construir o contexto dinamicamente
    context = {
        var_name: status_counts_dict.get(status_variables[var_name], 0)
        for var_name in status_variables
    }

    # Obter status_choices excluindo os indesejados
    status_exclude = ('em_espera', 'aguardando_atendimento')
    context['status_choices'] = [
        choice for choice in Execucao.STATUS_CHOICES if choice[0] not in status_exclude
    ]

    # Adicionar os setores ao contexto
    context['setores'] = Setor.objects.all()
    
    context['quantidade_atrasada'] = quantidade_atrasada(filtros)
    context['operadores'] = operadores_all('producao')

    return render(request, 'solicitacoes/solicitacao-producao.html', context)

@login_required
def home_predial(request):
    # Definir filtros iniciais
    base_filters = (Q(status__isnull=True) | Q(status='aprovar')) & Q(area='predial')

    # Filtrar por solicitante se o usuário for um 'solicitante'
    if request.user.tipo_acesso == 'solicitante':
        base_filters &= Q(solicitante=request.user)
        filtros={'solicitante_id':request.user.id,'area':'predial'}
    else:
        filtros={'area':'predial'}

    # Obter as solicitações com base nos filtros
    solicitacoes = Solicitacao.objects.filter(base_filters)

    # Anotar contagens de status_andamento
    status_counts = solicitacoes.values('status_andamento').annotate(count=Count('id'))

    # Converter para um dicionário para acesso rápido
    status_counts_dict = {item['status_andamento']: item['count'] for item in status_counts}

    # Lista de status para facilitar o acesso
    status_list = [
        'em_espera',
        'finalizada',
        'em_execucao',
        'aguardando_material',
        'aguardando_atendimento'
    ]

    # Mapeamento dos nomes das variáveis para os status
    status_variables = {
        'quantidade_em_aberto': 'em_espera',
        'quantidade_finalizada': 'finalizada',
        'quantidade_em_execucao': 'em_execucao',
        'aguardando_material': 'aguardando_material',
        'aguardando_primeiro_atendimento_card': 'aguardando_atendimento',
    }

    # Construir o contexto dinamicamente
    context = {
        var_name: status_counts_dict.get(status_variables[var_name], 0)
        for var_name in status_variables
    }

    # Obter status_choices excluindo os indesejados
    status_exclude = ('em_espera', 'aguardando_atendimento')
    context['status_choices'] = [
        choice for choice in Execucao.STATUS_CHOICES if choice[0] not in status_exclude
    ]
    context['quantidade_atrasada'] = quantidade_atrasada(filtros)

    # Adicionar os setores ao contexto
    context['setores'] = Setor.objects.all()

    return render(request, 'solicitacoes/solicitacao-predial.html', context)

@login_required
def home_solicitante(request):

    return render(request,'solicitante/home.html')

@login_required
def solicitacoes_producao(request):

    numero_ordem = request.GET.get('ordem')
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.getlist('ultimo_status')
    planejada = request.GET.get('planejada')
    atrasada = request.GET.get('atrasada')
    responsavel = request.GET.get('responsavel')
    maquina = request.GET.get('maquina')

    base_filters = (Q(status__isnull=True) | Q(status='aprovar')) & Q(area='producao')

    # Se o usuário for solicitante, adicionar filtro adicional
    if request.user.tipo_acesso == 'solicitante':
        base_filters &= Q(solicitante=request.user)

    # Realizar a consulta otimizada
    solicitacoes = (
        Solicitacao.objects
        .filter(base_filters)
        .exclude(status_andamento='aguardando_atendimento')
        .select_related('solicitante', 'setor')  # Join nos campos ForeignKey
        .prefetch_related('fotos')  # Prefetch nos relacionamentos ManyToMany ou reverse FK
    )

    ultima_execucao_subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao')

    # Anotar a consulta de Solicitacao com o valor de n_execucao da última execução
    solicitacoes = solicitacoes.annotate(
        ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1]),
        ultima_atualizacao=Subquery(ultima_execucao_subquery.values('ultima_atualizacao')[:1])
    ).order_by('-ultima_atualizacao')

    if numero_ordem:
        solicitacoes = solicitacoes.filter(pk=numero_ordem)

    if solicitante:
        solicitacoes = solicitacoes.filter(solicitante__nome__icontains=solicitante)

    if setor_id:
        solicitacoes = solicitacoes.filter(setor_id=setor_id)

    if maq_parada:
        solicitacoes = solicitacoes.filter(maq_parada=(maq_parada == 'sim'))

    if data_abertura:
        solicitacoes = solicitacoes.filter(data_abertura__date=data_abertura)

    if planejada:
        solicitacoes = solicitacoes.filter(planejada=True)

    if status:
        solicitacoes = solicitacoes.filter(status_andamento__in=status)

    if atrasada:
        solicitacoes = solicitacoes.filter(
            programacao__lt= now().date(),
        ).exclude(status_andamento='finalizada')

    if responsavel:
        solicitacoes = solicitacoes.filter(atribuido_id=responsavel)
    
    if maquina:
        solicitacoes = solicitacoes.filter(maquina_id=maquina)

    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page', 1)  # Pega o número da página, ou assume 1 como padrão
    page_obj = paginator.get_page(page_number)
    next_page = page_obj.next_page_number() if page_obj.has_next() else None

    # Verifica se é uma requisição AJAX para "Carregar mais"
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Preparar o contexto com os dados necessários
        page_obj = paginator.get_page(page_number)
        context = {
            'page_obj': page_obj,
            'operadores': operadores_all('producao'),
            'status_choices': [choice for choice in Execucao.STATUS_CHOICES if choice[0] not in ('em_espera', 'aguardando_atendimento')],
            'area_manutencao': InfoSolicitacao.AREA_CHOICES,
            'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
            'nextPage': page_obj.next_page_number() if page_obj.has_next() else None,
            'today': timezone.now().date()  # Data atual sem hora
        }

        # Renderiza o conteúdo da página parcial como HTML
        html = render_to_string('solicitacoes/partials/cards-producao.html', context, request=request)
        
        # Retorna a resposta em JSON contendo o HTML e o número da próxima página
        return JsonResponse({
            'html': html,
            'nextPage': next_page  # Retorna nextPage para o controle no frontend
        })

    # Contexto para renderizar normalmente
    context = {
        'page_obj': page_obj,
        'operadores': operadores_all('producao'),
        'status_choices': [choice for choice in Execucao.STATUS_CHOICES if choice[0] not in ('em_espera', 'aguardando_atendimento')],
        'area_manutencao': InfoSolicitacao.AREA_CHOICES,
        'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
        'nextPage': next_page,
        'today': timezone.now().date()  # Data atual sem hora

    }

    # Renderiza a página completa no caso de não ser uma requisição AJAX
    return render(request, 'solicitacoes/partials/cards-producao.html', context)

@login_required
def aguardando_primeiro_atendimento_producao(request):

    numero_ordem = request.GET.get('ordem')
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.getlist('ultimo_status')
    planejada = request.GET.get('planejada')
    maquina = request.GET.get('maquina')

    print(status)

    # Inicia o queryset base
    aguardando_primeiro_atendimento = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar'), 
        area='producao',
        status_andamento='aguardando_atendimento'
    ).select_related('solicitante', 'setor').prefetch_related('fotos', 'info_solicitacao').order_by('-data_abertura')

    if request.user.tipo_acesso == 'solicitante':
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(solicitante=request.user)

    if numero_ordem:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(pk=numero_ordem)

    if solicitante:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(solicitante__nome__icontains=solicitante)

    if setor_id:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(setor_id=setor_id)

    if maq_parada:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(maq_parada=(maq_parada == 'sim'))

    if data_abertura:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(data_abertura__date=data_abertura)

    if planejada:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(planejada=True)

    if status:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(status_andamento__in=status)

    if maquina:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(maquina_id=maquina)

    # Paginação
    paginator = Paginator(aguardando_primeiro_atendimento, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    next_page = page_obj.next_page_number() if page_obj.has_next() else None

    # Contexto
    context = {
        'page_obj': page_obj,
        'nextPage': next_page,
        'aguardando_primeiro_atendimento': aguardando_primeiro_atendimento,
        'area_manutencao': InfoSolicitacao.AREA_CHOICES,
        'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
        'today': timezone.now().date(),  # Data atual sem hora
        'operadores': Operador.objects.filter(area='producao', status='ativo'),
        'request':request
    }

    # Verifica se é uma requisição AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        page_obj = paginator.get_page(page_number)
        context = {
            'page_obj': page_obj,
            'nextPage': page_obj.next_page_number() if page_obj.has_next() else None,
            'area_manutencao': InfoSolicitacao.AREA_CHOICES,
            'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
            'today': timezone.now().date(),  # Data atual sem hora
            'operadores': Operador.objects.filter(area='producao', status='ativo'),
            'request':request
        }

        html = render_to_string('solicitacoes/partials/cards-producao-aguardando.html', context)

        return JsonResponse({'html': html, 'nextPage': next_page})

    # Renderização normal
    return render(request, 'solicitacoes/partials/cards-producao-aguardando.html', context)

@login_required
def maquinas_paradas_producao(request):
    # Obtenção das máquinas paradas
    maquinas = dict(maquinas_paradas())

    context = {
        'maquinas': maquinas,
    }

    return render(request, 'solicitacoes/partials/cards-maq-paradas.html', context)

@login_required
def solicitacoes_predial(request):

    ordem = request.GET.get('ordem')
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    # maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.getlist('ultimo_status')
    planejada = request.GET.get('planejada')
    atrasada = request.GET.get('atrasada')

    base_filters = (Q(status__isnull=True) | Q(status='aprovar')) & Q(area='predial')

    # Se o usuário for solicitante, adicionar filtro adicional
    if request.user.tipo_acesso == 'solicitante':
        base_filters &= Q(solicitante=request.user)

    # Realizar a consulta otimizada
    solicitacoes = (
        Solicitacao.objects
        .filter(base_filters)
        .exclude(status_andamento='aguardando_atendimento')
        .select_related('solicitante', 'setor')  # Join nos campos ForeignKey
        .prefetch_related('fotos')  # Prefetch nos relacionamentos ManyToMany ou reverse FK
    )

    ultima_execucao_subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao')

    # Anotar a consulta de Solicitacao com o valor de n_execucao da última execução
    solicitacoes = solicitacoes.annotate(
        ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1]),
        ultima_atualizacao=Subquery(ultima_execucao_subquery.values('ultima_atualizacao')[:1])

    )

    if ordem:
        solicitacoes = solicitacoes.filter(pk=ordem)

    if solicitante:
        solicitacoes = solicitacoes.filter(solicitante__nome__icontains=solicitante)

    if setor_id:
        solicitacoes = solicitacoes.filter(setor_id=setor_id)

    # if maq_parada:
    #     solicitacoes = solicitacoes.filter(maq_parada=(maq_parada == 'sim'))

    if data_abertura:
        solicitacoes = solicitacoes.filter(data_abertura__date=data_abertura)

    if planejada:
        solicitacoes = solicitacoes.filter(planejada=True)

    if status:
        solicitacoes = solicitacoes.filter(status_andamento__in=status)

    if atrasada:
        solicitacoes = solicitacoes.filter(
            programacao__lt= now().date(),
        ).exclude(status_andamento='finalizada')

    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page', 1)  # Pega o número da página, ou assume 1 como padrão
    page_obj = paginator.get_page(page_number)
    next_page = page_obj.next_page_number() if page_obj.has_next() else None

    # Verifica se é uma requisição AJAX para "Carregar mais"
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Preparar o contexto com os dados necessários
        page_obj = paginator.get_page(page_number)
        context = {
            'page_obj': page_obj,
            'operadores': operadores_all('predial'),
            'status_choices': [choice for choice in Execucao.STATUS_CHOICES if choice[0] not in ('em_espera', 'aguardando_atendimento')],
            'area_manutencao': InfoSolicitacao.AREA_CHOICES,
            'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
            'nextPage': page_obj.next_page_number() if page_obj.has_next() else None,
            'today': timezone.now().date()  # Data atual sem hora
        }

        # Renderiza o conteúdo da página parcial como HTML
        html = render_to_string('solicitacoes/partials/cards-predial.html', context, request=request)
        
        # Retorna a resposta em JSON contendo o HTML e o número da próxima página
        return JsonResponse({
            'html': html,
            'nextPage': next_page  # Retorna nextPage para o controle no frontend
        })

    # Contexto para renderizar normalmente
    context = {
        'page_obj': page_obj,
        'operadores': operadores_all('predial'),
        'status_choices': [choice for choice in Execucao.STATUS_CHOICES if choice[0] not in ('em_espera', 'aguardando_atendimento')],
        'area_manutencao': InfoSolicitacao.AREA_CHOICES,
        'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
        'nextPage': next_page,
        'today': timezone.now().date()  # Data atual sem hora

    }

    # Renderiza a página completa no caso de não ser uma requisição AJAX
    return render(request, 'solicitacoes/partials/cards-predial.html', context)

@login_required
def aguardando_primeiro_atendimento_predial(request):
    
    ordem = request.GET.get('ordem')
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    # maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.getlist('ultimo_status')
    planejada = request.GET.get('planejada')

    # Inicia o queryset base
    aguardando_primeiro_atendimento = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar'),
        area='predial',
        status_andamento='aguardando_atendimento'
    ).select_related('solicitante', 'setor').prefetch_related('fotos', 'info_solicitacao')

    if ordem:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(pk=ordem)

    if solicitante:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(solicitante__nome__icontains=solicitante)

    if setor_id:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(setor_id=setor_id)

    # if maq_parada:
    #     aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(maq_parada=(maq_parada == 'sim'))

    if data_abertura:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(data_abertura__date=data_abertura)

    if planejada:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(planejada=True)

    if status:
        aguardando_primeiro_atendimento = aguardando_primeiro_atendimento.filter(status_andamento__in=status)

    # Paginação
    paginator = Paginator(aguardando_primeiro_atendimento, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    next_page = page_obj.next_page_number() if page_obj.has_next() else None

    # Contexto
    context = {
        'page_obj': page_obj,
        'nextPage': next_page,
        'aguardando_primeiro_atendimento': aguardando_primeiro_atendimento,
        'area_manutencao': [('predial', 'Predial')],
        'tipo_manutencao': [('corretiva', 'Corretiva'),('planejada','Planejada'),('projetos','Projetos')],
        'operadores': Operador.objects.filter(area='predial', status='ativo'),
    }

    # Verifica se é uma requisição AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        page_obj = paginator.get_page(page_number)
        context = {
            'page_obj': page_obj,
            'nextPage': page_obj.next_page_number() if page_obj.has_next() else None,
            'area_manutencao': [('predial', 'Predial')],
            'tipo_manutencao': [('corretiva', 'Corretiva'),('planejada','Planejada'),('projetos','Projetos')],
            'operadores': Operador.objects.filter(area='predial', status='ativo'),
        }

        html = render_to_string('solicitacoes/partials/cards-predial-aguardando.html', context)

        return JsonResponse({'html': html, 'nextPage': next_page})

    # Renderização normal
    return render(request, 'solicitacoes/partials/cards-predial-aguardando.html', context)

def reenviar_mensagem(request, ordem_id):
    try:
        # Busca a solicitação pelo ID
        solicitacao = get_object_or_404(Solicitacao, pk=ordem_id)

        # Busca o telefone do solicitante
        telefone = buscar_telefone(solicitacao.solicitante.matricula)
        
        # Constrói o link para a página de satisfação
        link_satisfacao = request.build_absolute_uri(reverse('pagina_satisfacao', args=[solicitacao.pk]))

        # Busca a última execução relacionada à solicitação
        ultima_execucao = Execucao.objects.filter(ordem=solicitacao).order_by('-n_execucao').first()

        # Verifica se o telefone foi encontrado e se há uma última execução
        if telefone and ultima_execucao:
            kwargs = {
                'ordem': solicitacao.pk,
                'data_abertura': solicitacao.data_abertura,
                'data_fechamento': ultima_execucao.data_fim,
                'maquina': solicitacao.maquina.codigo,
                'motivo': solicitacao.descricao,
                'descricao': solicitacao.maquina.descricao,
                'link': link_satisfacao
            }

            # Instancia o serviço de WhatsApp
            ordem_service = OrdemServiceWpp()

            # Envia a mensagem via WhatsApp
            status_code, response_data = ordem_service.reenviar_mensagem_finalizar_ordem(telefone, kwargs)
            return JsonResponse({'success': True, 'response': response_data}, status=status_code)
        else:
            return JsonResponse({'error': 'Telefone não encontrado ou execução não disponível'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def historico_ordem(request, pk):
    # Consulta para buscar execuções com operadores relacionados
    data = (
        Execucao.objects
        .filter(ordem_id=pk)
        .prefetch_related('operador')  # Carrega operadores relacionados
        .values('id','n_execucao', 'data_inicio', 'data_fim', 'observacao', 'ultima_atualizacao', 
                'che_maq_parada', 'exec_maq_parada', 'apos_exec_maq_parada', 'status')
    ).order_by('n_execucao')

    data_list = []
    for execucao in data:
        execucao_dict = execucao
        operadores = Execucao.objects.get(pk=execucao['id']).operador.filter(status='ativo').values_list('nome', flat=True)
        execucao_dict['operadores'] = list(operadores)
        data_list.append(execucao_dict)

    return JsonResponse({'historico': data_list})

def dados_editar_execucao(request, pk):
    # Consulta para buscar execuções com operadores relacionados
    data = (
        Execucao.objects
        .filter(id=pk)
        .prefetch_related('operador')  # Carrega operadores relacionados
        .values('id','n_execucao','data_inicio', 'data_fim', 'observacao', 'ultima_atualizacao', 
                'che_maq_parada', 'exec_maq_parada', 'apos_exec_maq_parada', 'status')
    ).order_by('n_execucao')

    data_list = []
    for execucao in data:
        execucao_dict = execucao
        operadores = Execucao.objects.get(pk=execucao['id']).operador.filter(status='ativo').values_list('nome', flat=True)
        execucao_dict['operadores'] = list(operadores)
        data_list.append(execucao_dict)

    todos_operadores = operadores_all('producao')
    operadores = list(todos_operadores.values('id', 'nome'))  # Converte para uma lista de dicionários

    return JsonResponse({'dados': data_list, 'operadores': operadores})

def mais_detalhes_ordem(request, pk):
    # Consulta para buscar execuções com operadores relacionados
    solicitacoes = Solicitacao.objects.filter(pk=pk).select_related(
        'atribuido',  # Relacionamento com Operador
        'maquina',    # Relacionamento com Maquina
        'setor',      # Relacionamento com Setor
        'solicitante' # Relacionamento com Funcionario
    ).annotate(
        nome_solicitante=F('solicitante__nome'),
        setor_nome=F('setor__nome'),
        operador_responsavel=F('atribuido__nome'),
        nome_maquina=Concat(F('maquina__codigo'), Value(' - '), F('maquina__descricao'))
    ).values(
        'nome_solicitante',
        'setor_nome',
        'codigo_ferramenta',
        'tipo_ferramenta',
        'equipamento_em_falha',
        'setor_maq_solda',
        'impacto_producao',
        'descricao',
        'data_abertura',
        'status_andamento',
        'programacao',
        'operador_responsavel',
        'nome_maquina'
    )

    return JsonResponse({'solicitacoes': list(solicitacoes)})

def editar_execucao(request, pk):
    if request.method == "POST":
        with transaction.atomic():
            try:
                # Decodifica o corpo da requisição JSON
                data = json.loads(request.body)

                nova_data_inicio = parse_datetime(data['data_inicio'])
                nova_data_fim = parse_datetime(data['data_fim'])
                nova_observacao = data['observacao']

                # Obter a execução atual
                execucao = get_object_or_404(Execucao, pk=pk)

                print("exec: ",execucao)

                # Obter a última execução anterior, se existir
                ultima_execucao_anterior = (
                    Execucao.objects.filter(
                        ordem=execucao.ordem,
                        n_execucao__lt=execucao.n_execucao
                    )
                    .order_by('-n_execucao')
                    .first()
                )

                proxima_execucao = (
                    Execucao.objects.filter(
                        ordem=execucao.ordem,  # Filtra pela mesma ordem
                        n_execucao__gt=execucao.n_execucao  # Filtra para pegar execuções com número maior que o número da execução atual
                    )
                    .order_by('n_execucao')  # Ordena os resultados pela coluna `n_execucao` em ordem crescente
                    .first()  # Pega o primeiro resultado (a próxima execução com o maior número de execução)
                )

                # Validar as novas datas em relação à última execução anterior
                if ultima_execucao_anterior:
                    # Normalizar as datas (remover ou adicionar fuso horário conforme necessário)
                    if is_naive(nova_data_inicio):
                        nova_data_inicio = make_aware(nova_data_inicio)
                    if is_naive(ultima_execucao_anterior.data_fim):
                        ultima_execucao_anterior.data_fim = make_aware(ultima_execucao_anterior.data_fim)

                    # Verificação de datas
                    print(nova_data_inicio)
                    print(ultima_execucao_anterior.data_fim)

                    if nova_data_inicio <= ultima_execucao_anterior.data_fim:
                        return JsonResponse({
                            "error": "A nova data de início deve ser posterior à data final da última execução anterior."
                        }, status=400)
                
                if proxima_execucao:
                    if is_naive(nova_data_inicio):
                        nova_data_inicio = make_aware(nova_data_inicio)
                    if is_naive(proxima_execucao.data_inicio):
                        proxima_execucao.data_inicio = make_aware(proxima_execucao.data_inicio)

                    # Verificação de datas
                    print(nova_data_inicio)
                    print(proxima_execucao.data_inicio)

                    if nova_data_inicio >= proxima_execucao.data_inicio:
                        return JsonResponse({
                            "error": "A nova data de início deve ser anterior à data início da próxima execução."
                        }, status=400)

                # Validar que a nova data de fim seja posterior à data de início
                if nova_data_fim <= nova_data_inicio:
                    return JsonResponse({
                        "error": "A nova data de fim deve ser posterior à nova data de início."
                    }, status=400)

                # Atualizar registros na tabela `MaquinaParada`, se aplicável
                atualizar_registros(pk, nova_data_inicio, nova_data_fim)

                # Editar o registro na tabela `Execucao`
                Execucao.objects.filter(pk=pk).update(
                    data_fim=nova_data_fim,
                    data_inicio=nova_data_inicio,
                    observacao=nova_observacao,
                    ultima_atualizacao=now()
                )

                # Atualizar operadores
                novos_operadores_ids = data.get("operadores", [])
                novos_operadores = Operador.objects.filter(id__in=novos_operadores_ids)
                execucao.operador.set(novos_operadores)

                return JsonResponse({"status": "sucesso", "ordem": execucao.ordem_id})
            
            except Exception as e:
                return JsonResponse({
                    "error": f"Ocorreu um erro ao editar a execução: {str(e)}"
                }, status=500)
            
def atualizar_registros(pk, nova_data_inicio, nova_data_fim):
    # Obter o registro atual
    registro_atual = MaquinaParada.objects.filter(execucao_id=pk).select_related('execucao').first()

    if not registro_atual:
        return 'Não teve registro de máquina parada'
    
    # Atualizar o registro atual
    registro_atual.data_inicio = nova_data_inicio
    if registro_atual.data_fim:
        registro_atual.data_fim = nova_data_fim
    
    registro_atual.save()

    # Buscar o registro imediatamente anterior
    registro_anterior = (
        MaquinaParada.objects.filter(
            ordem_id=registro_atual.ordem_id,
            execucao__n_execucao__lt=registro_atual.execucao.n_execucao  # Apenas execuções anteriores
        )
        .order_by('-execucao__n_execucao')  # Ordenar decrescente por n_execucao para pegar o mais próximo
        .first()
    )

    # Atualizar o registro anterior, caso exista
    if registro_anterior:
        registro_anterior.data_fim = nova_data_inicio
        registro_anterior.save()
