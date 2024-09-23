from django.shortcuts import render
from django.db.models import OuterRef, Subquery, Value, IntegerField, Q
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
    subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao').values('n_execucao')[:1]

    solicitacoes = Solicitacao.objects.filter(
        Q(status__isnull=True) | Q(status='aprovar')
    )

    # Consulta das solicitações na área 'producao' com o número da última execução
    solicitacoes = solicitacoes.filter(
        area='producao',
    ).annotate(
        ultimo_numero_execucao=Coalesce(Subquery(subquery, output_field=IntegerField()), Value(0)),
        ultimo_status=Coalesce(Subquery(
            Execucao.objects.filter(ordem=OuterRef('pk')).order_by('-n_execucao').values('status')[:1]
        ), Value('aguardando_primeiro_atendimento'))
    )

    # Aplicando filtros
    solicitante = request.GET.get('solicitante')
    setor_id = request.GET.get('setor')
    maq_parada = request.GET.get('maq_parada')
    data_abertura = request.GET.get('data_abertura')
    status = request.GET.get('ultimo_status')
    planejada = request.GET.get('planejada')

    if solicitante:
        solicitacoes = solicitacoes.filter(solicitante__nome__icontains=solicitante,)
    
    if setor_id:
        solicitacoes = solicitacoes.filter(setor_id=setor_id,)
    
    if maq_parada:
        if maq_parada == 'sim':
            solicitacoes = solicitacoes.filter(maq_parada=True,)
        elif maq_parada == 'nao':
            solicitacoes = solicitacoes.filter(maq_parada=False,)
    
    if data_abertura:
        solicitacoes = solicitacoes.filter(data_abertura=data_abertura,)

    if planejada:
        solicitacoes = solicitacoes.filter(planejada=True,)

    aguardando_primeiro_atendimento = solicitacoes.filter(ultimo_status='aguardando_primeiro_atendimento')

    if status:
        solicitacoes = solicitacoes.filter(ultimo_status=status,)

    solicitacoes = solicitacoes.filter(~Q(ultimo_status='aguardando_primeiro_atendimento'))

    # Paginação
    paginator = Paginator(solicitacoes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Paginação sem filtro
    paginator_not_filter = Paginator(solicitacoes.filter(~Q(ultimo_status='finalizada'),), 10)
    page_number_not_filter = request.GET.get('page')
    page_obj_not_filter = paginator_not_filter.get_page(page_number_not_filter)

    operadores = operadores_all('producao')
    status_choices = list(Execucao.STATUS_CHOICES)
    status_choices = [choice for choice in status_choices if choice[0] not in ('em_espera', 'aguardando_atendimento')]
    tipo_manutencao = InfoSolicitacao.TIPO_CHOICES
    area_manutencao = InfoSolicitacao.AREA_CHOICES

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':

        html = render_to_string('cards/cards-producao.html', {'page_obj': page_obj, 
                                                              'operadores':operadores,
                                                              'status_choices':status_choices,
                                                              'area_manutencao':area_manutencao,
                                                              'tipo_manutencao':tipo_manutencao,})
        
        html_maquinas_paradas = render_to_string('cards/cards-maq-paradas.html', {'maquinas':dict(maquinas_paradas())})

        html_aguardando_primeiro_atendimento = render_to_string('cards/cards-producao-aguardando.html', {'aguardando_primeiro_atendimento':aguardando_primeiro_atendimento})

        # Verifique se há uma próxima página
        next_page = page_obj.next_page_number() if page_obj.has_next() else None

        return JsonResponse({
            'html': html,
            'html_maquinas_paradas': html_maquinas_paradas,
            'html_aguardando_primeiro_atendimento':html_aguardando_primeiro_atendimento,
            'nextPage': next_page
        })

    # Obtenção de todos os setores para o filtro
    setores = Setor.objects.all()

    context = {
        'page_obj': page_obj_not_filter,
        'operadores': operadores,
        'status_choices': status_choices,
        'area_manutencao':area_manutencao,
        'tipo_manutencao':tipo_manutencao,
        'quantidade_em_aberto': solicitacoes.filter(ultimo_status='em_espera').count(),
        'quantidade_finalizada': solicitacoes.filter(ultimo_status='finalizada').count(),
        'quantidade_em_execucao': solicitacoes.filter(ultimo_status='em_execucao').count(),
        'aguardando_primeiro_atendimento_card': aguardando_primeiro_atendimento.count(),
        'setores': setores,
        'solicitante': solicitante,
        'setor_id': setor_id,
        'maq_parada': maq_parada,
        'data_abertura': data_abertura,
        'planejada':planejada,

        'maquinas':dict(maquinas_paradas()),
        'aguardando_primeiro_atendimento': aguardando_primeiro_atendimento,
        

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