from django.shortcuts import render
from django.db.models import OuterRef, Subquery, Value, IntegerField, Q, Count
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao
from cadastro.models import Setor, Operador

from .utils import *

@login_required
def home_producao(request):

    # Subquery para obter o número da última execução para cada solicitação
    solicitacoes = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar'),
    )

    context = {
        'quantidade_em_aberto': solicitacoes.filter(status_andamento='em_espera').count(),
        'quantidade_finalizada': solicitacoes.filter(status_andamento='finalizada').count(),
        'quantidade_em_execucao': solicitacoes.filter(status_andamento='em_execucao').count(),
        'aguardando_material': solicitacoes.filter(status_andamento='aguardando_material').count(),
        'aguardando_primeiro_atendimento_card': solicitacoes.filter(status_andamento='aguardando_atendimento').count(),

    }

    return render(request, 'solicitacoes/solicitacao-producao.html', context)

@login_required
def home_predial(request):

    # Subquery para obter o status da última execução para cada solicitação
    subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao').values('n_execucao')[:1]

    # Consulta das solicitações na área 'producao' com o status da última execução
    solicitacoes = Solicitacao.objects.filter(area='predial').annotate(
        ultimo_numero_execucao=Coalesce(Subquery(subquery, output_field=IntegerField()), Value(0)),
        ultimo_status=Coalesce(Subquery(
                Execucao.objects.filter(ordem=OuterRef('pk')).order_by('-n_execucao').values('status')[:1]
            ), Value('em_espera'))
    )

    # Aplicando filtros
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.get('ultimo_status')

    if solicitante:
        solicitacoes = solicitacoes.filter(solicitante__nome__icontains=solicitante)
    
    if setor_id:
        solicitacoes = solicitacoes.filter(setor_id=setor_id)
    
    if data_abertura:
        solicitacoes = solicitacoes.filter(data_abertura=data_abertura)

    if status:  # Filtro para o status
        solicitacoes = solicitacoes.filter(ultimo_status=status)

    # Paginação
    paginator = Paginator(solicitacoes, 10)  # Exibir 10 solicitações por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Paginação sem filtro
    paginator_not_filter = Paginator(solicitacoes.filter(~Q(ultimo_status='finalizada')), 10)  # Exibir 10 solicitações por página
    page_number_not_filter = request.GET.get('page')
    page_obj_not_filter = paginator_not_filter.get_page(page_number_not_filter)

    operadores = operadores_all('predial')
    status_choices = list(Execucao.STATUS_CHOICES)
    status_choices = [choice for choice in status_choices if choice[0] != 'em_espera']
    tipo_manutencao = InfoSolicitacao.TIPO_CHOICES

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('cards/cards-predial.html', {'page_obj': page_obj,
                                                             'status_choices':status_choices,
                                                             'tipo_manutencao':tipo_manutencao,
                                                             'operadores':operadores})
        
        # Verifique se há uma próxima página
        next_page = page_obj.next_page_number() if page_obj.has_next() else None

        return JsonResponse({
            'html': html,
            'nextPage': next_page
        })
    
    setores = Setor.objects.all()

    context = {
        'page_obj': page_obj_not_filter,
        'status_choices':status_choices,
        'tipo_manutencao':tipo_manutencao,
        'operadores':operadores,
        'quantidade_em_aberto': solicitacoes.filter(ultimo_status='em_espera').count(),
        'quantidade_finalizada': solicitacoes.filter(ultimo_status='finalizada').count(),
        'quantidade_em_execucao': solicitacoes.filter(ultimo_status='em_execucao').count(),
        'setores': setores,
        'solicitante': solicitante,
        'setor_id': setor_id,
        'data_abertura': data_abertura,
    }
    return render(request, 'solicitacoes/solicitacao-predial.html', context)

@login_required
def home_solicitante(request):

    return render(request,'solicitante/home.html')

@login_required
def solicitacoes_producao(request):

    solicitacoes = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar')
    ).exclude(status_andamento='aguardando_atendimento')

    ultima_execucao_subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao')

    # Anotar a consulta de Solicitacao com o valor de n_execucao da última execução
    solicitacoes = solicitacoes.annotate(
        ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1])
    ).exclude(status_andamento='aguardando_atendimento')

    # Aplicando filtros
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.get('ultimo_status')
    planejada = request.GET.get('planejada')

    if solicitante:
        solicitacoes = solicitacoes.filter(solicitante__nome__icontains=solicitante)

    if setor_id:
        solicitacoes = solicitacoes.filter(setor_id=setor_id)

    if maq_parada:
        solicitacoes = solicitacoes.filter(maq_parada=(maq_parada == 'sim'))

    if data_abertura:
        solicitacoes = solicitacoes.filter(data_abertura=data_abertura)

    if planejada:
        solicitacoes = solicitacoes.filter(planejada=True)

    if status:
        solicitacoes = solicitacoes.filter(status_andamento=status)
    else:
        solicitacoes = solicitacoes.exclude(status_andamento='aguardando_atendimento')

    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Contexto
    context = {
        'page_obj': page_obj,
        'operadores': operadores_all('producao'),
        'status_choices': [choice for choice in Execucao.STATUS_CHOICES if choice[0] not in ('em_espera', 'aguardando_atendimento')],
        'area_manutencao': InfoSolicitacao.AREA_CHOICES,
        'tipo_manutencao': InfoSolicitacao.TIPO_CHOICES,
    }

    # # Renderização para AJAX
    # if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    #     html = render_to_string('solicitacoes/partials/cards-producao.html', context, request=request)
    #     next_page = page_obj.next_page_number() if page_obj.has_next() else None
    #     return JsonResponse({'html': html, 'nextPage': next_page})

    return render(request, 'solicitacoes/partials/cards-producao.html', context)

@login_required
def aguardando_primeiro_atendimento_producao(request):

    solicitacoes = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar')
    )

    aguardando_primeiro_atendimento = solicitacoes.filter(status_andamento='aguardando_atendimento')

    context = {
        'aguardando_primeiro_atendimento': aguardando_primeiro_atendimento,
    }

    return render(request, 'solicitacoes/partials/cards-producao-aguardando.html', context)

@login_required
def maquinas_paradas_producao(request):
    # Obtenção das máquinas paradas
    maquinas = dict(maquinas_paradas())

    context = {
        'maquinas': maquinas,
    }

    # Renderização para AJAX
    # if request.headers.get('x-requested-with') == 'XMLHttpRequest':
    #     html = render_to_string('solicitacoes/partials/cards-maq-paradas.html', context, request=request)
    #     return JsonResponse({'html': html})

    return render(request, 'solicitacoes/partials/cards-maq-paradas.html', context)
