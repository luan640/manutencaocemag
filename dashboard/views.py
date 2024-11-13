from django.http import JsonResponse
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField, Avg, Min, Max, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils.timezone import now, timedelta
from django.db.models import Sum, F, ExpressionWrapper, DurationField, OuterRef, Subquery
from django.utils.functional import SimpleLazyObject
from django.utils import timezone

from solicitacao.models import Solicitacao
from execucao.models import Execucao, MaquinaParada, InfoSolicitacao
from cadastro.models import Maquina, Setor

from datetime import datetime

def dashboard(request):

    setores = Setor.objects.all()

    return render(request, 'dashboard.html', {'setores':setores})

def mtbf_maquina(request):
    
    """
    Calcula o MTBF (Mean Time Between Failures) de cada máquina para o mês atual e retorna os dados em formato JSON.

    O MTBF é uma métrica que representa o tempo médio entre falhas de uma máquina, dado pela fórmula:
        MTBF = (Tempo de atividade esperada - Tempo total de paradas) / Quantidade de paradas

    Parâmetros:
    -----------
    request : HttpRequest
        Objeto de requisição HTTP padrão do Django.

    Lógica:
    -------
    - Calcula o primeiro e último dia do mês atual.
    - Assume um tempo de atividade esperado de 9 horas por dia.
    - Busca as paradas finalizadas dentro do mês atual e agrupa por máquina.
    - Calcula o tempo total de paradas e a quantidade de paradas para cada máquina.
    - Usa esses dados para calcular o MTBF de cada máquina.
    - Retorna os resultados como uma lista JSON contendo o código da máquina e o MTBF arredondado para duas casas decimais.

    Retorno:
    --------
    JsonResponse
        Retorna uma lista de dicionários no formato:
        [
            {"maquina": "MAQ001", "mtbf": 12.5},
            {"maquina": "MAQ002", "mtbf": 9.8},
            ...
        ]
    """
        
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Tempo de atividade esperada: 9 horas por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    filtros = {
            'data_inicio__gte': data_inicio,
            'data_fim__lte': data_fim,
            'ordem__area': area,
        }
    if setor:
        filtros['ordem__setor_id'] = int(setor)

    # Buscar as paradas do mês atual e calcular a duração de cada uma
    paradas = (
        MaquinaParada.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')  # Agrupa pelo codigo da máquina
        .annotate(
            total_paradas=Sum('duracao'),  # Soma das durações das paradas
            quantidade_paradas=Count('id')  # Contagem de paradas
        )
    )

    # Preparar os dados para o JSON
    resultados = []
    for parada in paradas:
        tempo_total_paradas_horas = parada['total_paradas'].total_seconds() / 3600  # Converter para horas
        quantidade_paradas = parada['quantidade_paradas']

        # Cálculo do MTBF
        mtbf = (tempo_atividade_esperada - tempo_total_paradas_horas) / quantidade_paradas

        resultados.append({
            'maquina': parada['ordem__maquina__codigo'],
            'mtbf': round(mtbf, 2)
        })

    resultados = sorted(resultados, key=lambda x: x['mtbf'], reverse=True)

    return JsonResponse(resultados, safe=False)

def mttr_maquina(request):
    """
    Calcula o MTTR (Mean Time to Repair) para cada máquina no mês atual.

    O MTTR é calculado com base no tempo médio de reparo das execuções finalizadas.
    A fórmula utilizada é: 
        MTTR = (Tempo total de reparos) / (Quantidade de reparos)

    Retorna uma lista em formato JSON contendo o nome da máquina e seu respectivo MTTR em horas.
    Caso não haja execuções para alguma máquina, retorna "Sem dados" para o MTTR.

    Parâmetros:
    ----------
    request : HttpRequest
        A requisição HTTP recebida.

    Retorno:
    -------
    JsonResponse
        Uma lista de dicionários com os campos:
        - 'maquina': Código da máquina.
        - 'mttr': Tempo médio de reparo em horas ou "Sem dados" se não houver execuções.
    """

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)

    # Buscar execuções finalizadas no mês atual
    execucoes = (
        Execucao.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')
        .annotate(
            total_tempo_reparo=Sum('duracao'),  # Soma das durações
            quantidade_reparos=Count('id')  # Contagem de execuções
        )
    )

    # Preparar os dados para o JSON
    resultados = []
    for execucao in execucoes:
        tempo_total_reparo_horas = execucao['total_tempo_reparo'].total_seconds() / 3600  # Converter para horas
        quantidade_reparos = execucao['quantidade_reparos']

        # Verificar se há reparos para evitar divisão por zero
        if quantidade_reparos > 0:
            mttr = tempo_total_reparo_horas / quantidade_reparos
        else:
            mttr = None  # Não há execuções para calcular o MTTR

        # Adicionar no resultado
        resultados.append({
            'maquina': execucao['ordem__maquina__codigo'],
            'mttr': round(mttr, 2) if mttr is not None else 'Sem dados'
        })

    resultados = sorted(resultados, key=lambda x: x['mttr'], reverse=True)

    return JsonResponse(resultados, safe=False)

def disponibilidade_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Tempo de atividade esperada: 9 horas por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area

    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)

    # Buscar e calcular MTBF
    paradas = (
        MaquinaParada.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')
        .annotate(total_paradas=Sum('duracao'), quantidade_paradas=Count('id'))
    )

    # Buscar e calcular MTTR
    execucoes = (
        Execucao.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')
        .annotate(total_tempo_reparo=Sum('duracao'), quantidade_reparos=Count('id'))
    )

    # Organizar os dados em dicionários para fácil acesso
    mtbf_dict = {
        parada['ordem__maquina__codigo']: (parada['total_paradas'].total_seconds() / 3600, parada['quantidade_paradas'])
        for parada in paradas
    }
    mttr_dict = {
        execucao['ordem__maquina__codigo']: (execucao['total_tempo_reparo'].total_seconds() / 3600, execucao['quantidade_reparos'])
        for execucao in execucoes
    }

    # Calcular a disponibilidade para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        mttr = mttr_dict.get(maquina, (0, 1))[0] / mttr_dict.get(maquina, (0, 1))[1]  # Evitar divisão por 0
        mtbf = (tempo_atividade_esperada - tempo_total_paradas) / qtd_paradas if qtd_paradas > 0 else 0  # Tempo esperado de 9h/dia

        if mtbf + mttr > 0:
            disponibilidade = (mtbf / (mtbf + mttr)) * 100
        else:
            disponibilidade = 0

        resultados.append({
            'maquina': maquina,
            'disponibilidade': round(disponibilidade, 2)
        })

    resultados = sorted(resultados, key=lambda x: x['disponibilidade'], reverse=True)

    return JsonResponse(resultados, safe=False)

def ordens_prazo(request):

    """
    Retorna um indicador de ordens finalizadas dentro e fora do prazo.
    """

    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'status_andamento': 'finalizada',
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)

    # Subquery para pegar a última execução de cada solicitação
    ultima_execucao_subquery = (
        Execucao.objects.filter(ordem=OuterRef('pk'), ordem__area=area)
        .order_by('-data_fim')
        .values('data_fim')[:1]
    )

    # Filtra as solicitações que foram finalizadas
    solicitacoes = Solicitacao.objects.filter(**filtros).exclude(status='rejeitar')

    # Anota a última data de execução para cada solicitação
    solicitacoes = solicitacoes.annotate(
        ultima_data_fim=Subquery(ultima_execucao_subquery)
    )

    # Calcula as ordens dentro e fora do prazo
    dentro_do_prazo = solicitacoes.filter(ultima_data_fim__lte=F('programacao')).count()
    fora_do_prazo = solicitacoes.filter(ultima_data_fim__gt=F('programacao')).count()

    return JsonResponse({
        'dentro_do_prazo': dentro_do_prazo,
        'fora_do_prazo': fora_do_prazo
    })

def relacao_por_tipo_ordem(request):
    
    """
    Retorna a contagem de ordens finalizadas por tipo de manutenção.
    """

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'solicitacao__status_andamento': 'finalizada',
        'solicitacao__data_abertura__gte': data_inicio,
        'solicitacao__data_abertura__lte':data_fim,
        'solicitacao__area':area
    }
    if setor:
        filtros['solicitacao__setor_id'] = int(setor)

    # Filtrando apenas as ordens finalizadas e agrupando por tipo de manutenção
    ordens_por_tipo = (
        InfoSolicitacao.objects
        .filter(**filtros)
        .exclude(solicitacao__status='rejeitar')  # Apenas ordens finalizadas e nao rejeitadas
        .values('tipo_manutencao')  # Agrupando por tipo de manutenção
        .annotate(total=Count('id'))  # Contando o total de cada tipo
        .order_by('tipo_manutencao')
    )

    # Convertendo para uma lista de dicionários e retornando em JSON
    data = list(ordens_por_tipo)
    return JsonResponse({'data': data})

def maquina_parada(request):
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'data_inicio__gte': data_inicio,
        'ordem__area': area
    }

    # Adiciona o filtro para data_fim, mas permite que ela seja NULL para o cálculo posterior
    filtros['data_fim__lte'] = data_fim

    if setor:
        filtros['ordem__setor_id'] = int(setor)

    # Calcular a duração (diferença entre início e fim), usando Coalesce para lidar com valores nulos em data_fim
    total_por_maquina = (
        MaquinaParada.objects
        .filter(**filtros)
        .annotate(
            data_fim_real=Coalesce('data_fim', Value(timezone.now())),  # Substitui NULL por a data e hora atual
            duracao=ExpressionWrapper(
                F('data_fim_real') - F('data_inicio'), output_field=DurationField()
            )
        )
        .values('ordem__maquina__codigo')  # Agrupa pelo código da máquina
        .annotate(total_duracao=Sum('duracao'))  # Soma a duração por máquina
    )

    # Converter o resultado para uma lista de dicionários com as durações em horas
    resultado = [
        {
            'maquina': item['ordem__maquina__codigo'],
            'total_horas': item['total_duracao'].total_seconds() / 3600 if item['total_duracao'] else 0
        }
        for item in total_por_maquina
    ]

    return JsonResponse({'data': resultado })

def solicitacao_setor(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'data_abertura__gte': data_inicio,
        'data_abertura__lte': data_fim,
        'status':'aprovar',
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)

    resultado = (
        Solicitacao.objects
        .filter(**filtros)
        .values('setor__nome')  # Agrupar pelo nome do setor
        .annotate(total=Count('id'))  # Contar as solicitações por setor
        .order_by('setor__nome')  # Ordenar por nome do setor (opcional)

    )

    data = list(resultado)  # Converte o QuerySet em uma lista de dicionários

    data = sorted(data, key=lambda x: x['total'], reverse=True)

    return JsonResponse({'data': data})

def quantidade_abertura_ordens(request):

    """dentro do mês"""

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'data_abertura__range':[data_inicio,data_fim],
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)

    ordens = Solicitacao.objects.filter(**filtros).exclude(status='rejeitar').count()

    return JsonResponse({'data':ordens})

def quantidade_finalizada(request):

    """dentro do mês"""

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'status': 'finalizada',
        'data_fim__range': [data_inicio, data_fim],
        'ordem__area':area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)

    ordens = Execucao.objects.filter(**filtros).count()

    return JsonResponse({'data':ordens})

def quantidade_aguardando_material(request):

    """Geral sem filtro"""

    setor = request.GET.get('setor')
    area = request.GET.get('area')

    filtros = {
        'status': 'aguardando_material',
        'ordem__area': area
    }

    if setor:
        filtros['ordem__setor_id'] = int(setor)

    ordens = Execucao.objects.filter(**filtros).count()

    return JsonResponse({'data':ordens})

def quantidade_atrasada(filtros):

    if filtros is None:
        filtros = {}

    data_limite = timezone.now()  # ou datetime.date(2024, 11, 1) se desejar uma data fixa

    # Filtra as solicitações atrasadas e conta
    solicitacoes = Solicitacao.objects.filter(
        **filtros,
        programacao__isnull=False,
        programacao__lte=data_limite
    ).exclude(
        Q(status='rejeitar') | Q(status_andamento='finalizada')
    ).count()

    return solicitacoes

def quantidade_atrasada_view(request):

    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Define os filtros para a solicitação
    filtros={'area':area}
    if setor:
        filtros['setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido

    fora_do_prazo = quantidade_atrasada(filtros)

    return JsonResponse({'data': fora_do_prazo})

def quantidade_em_execucao(request):

    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Define os filtros para a solicitação
    filtros = {'ordem__area':area,'status': 'em_execucao'}
    if setor:
        filtros['ordem__setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido

    ordens = Execucao.objects.filter(status='em_execucao').count()

    return JsonResponse({'data':ordens})

def tempo_medio_finalizar(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Define os filtros para a solicitação
    filtros = {'status': 'finalizada',
                'ordem__status':'aprovar',
                'ordem__data_abertura__gte':data_inicio,
                'data_fim__lte':data_fim,
                'ordem__area':area}
    
    if setor:
        filtros['ordem__setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido

    tempo_medio = (
        Execucao.objects
        .filter(**filtros)  # Aplica os filtros necessários
        .annotate(
            diferenca=ExpressionWrapper(
                F('data_fim') - F('ordem__data_abertura'),
                output_field=DurationField()
            )
        )
        .aggregate(media_diferenca=Avg('diferenca'))
    )

    # Extrai o valor da média
    media_duracao = tempo_medio['media_diferenca']

    # Formata o tempo de maneira amigável
    if media_duracao:
        dias = media_duracao.days
        horas = media_duracao.seconds // 3600
        minutos = (media_duracao.seconds % 3600) // 60
        media_duracao_formatada = f"{dias}D:{horas}H:{minutos}M"
    else:
        media_duracao_formatada = "Tempo médio não disponível para o intervalo selecionado."

    return JsonResponse({'data': media_duracao_formatada})

def tempo_medio_abertura(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')

    # Define os filtros para a solicitação
    filtros = {'data_abertura__gte': data_inicio,
                'data_abertura__lte':data_fim,
                'area':area
    }    
    
    if setor:
        filtros['setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido

    # Obtém a data da primeira e da última ordem aberta e a contagem total de ordens
    valores = Solicitacao.objects.filter(**filtros).aggregate(
        primeira_abertura=Min('data_abertura'),
        ultima_abertura=Max('data_abertura'),
        total_ordens=Count('id')
    )

    # Extrai os valores das datas e da contagem
    primeira_abertura = valores['primeira_abertura']
    ultima_abertura = valores['ultima_abertura']
    total_ordens = valores['total_ordens']

    # Calcula a diferença total entre a última e a primeira ordem
    if primeira_abertura and ultima_abertura and total_ordens > 1:
        diferenca_total = ultima_abertura - primeira_abertura
        # Divide pelo número total de ordens menos 1 para obter o tempo médio
        tempo_medio = diferenca_total / (total_ordens - 1)

        # Formata o tempo médio em dias e horas
        dias = tempo_medio.days
        horas = tempo_medio.seconds // 3600
        minutos = (tempo_medio.seconds % 3600) // 60
        tempo_medio_formatado = f"{dias}D:{horas}H:{minutos}M"

    else:
        tempo_medio_formatado = "00:00"  # Valor padrão se não houver dados suficientes

    return JsonResponse({'data': tempo_medio_formatado})

def horas_trabalhadas_setor(request):

    area = request.GET.get('area')

    resultado = Execucao.objects.filter(data_fim__isnull=False, ordem__area=area).annotate(
        dif_tempo=ExpressionWrapper(
            F('data_fim') - F('data_inicio'), 
            output_field=DurationField()
        )
    ).values('ordem__setor__nome').annotate(
        total_horas=Sum('dif_tempo')
    ).order_by('ordem__setor__nome')

    # Converte `total_horas` para horas decimais
    resultado_formatado = []
    for item in resultado:
        setor = item['ordem__setor__nome']
        total_horas = item['total_horas']
        
        if total_horas:
            # Converte para timedelta e depois para horas decimais
            duracao = timedelta(seconds=total_horas.total_seconds())
            horas_decimais = duracao.total_seconds() / 3600  # Total de horas em formato decimal
        else:
            horas_decimais = 0
        
        resultado_formatado.append({
            'setor': setor,
            'total_horas': horas_decimais
        })

    resultado_formatado = sorted(resultado_formatado, key=lambda x: x.get('total_horas', 0), reverse=True)

    # Retorna o resultado em formato JSON para o frontend
    return JsonResponse({'data': resultado_formatado})

def horas_trabalhadas_tipo(request):

    area = request.GET.get('area')

    resultado = Execucao.objects.filter(
        data_fim__isnull=False,
        ordem__info_solicitacao__tipo_manutencao__isnull=False,
        ordem__area=area
    ).annotate(
        dif_tempo=ExpressionWrapper(
            F('data_fim') - F('data_inicio'), 
            output_field=DurationField()
        )
    ).values('ordem__info_solicitacao__tipo_manutencao').annotate(
        total_horas=Sum('dif_tempo')
    ).order_by('ordem__info_solicitacao__tipo_manutencao')

    # Converte `total_horas` para horas decimais
    resultado_formatado = []
    for item in resultado:
        tipo_manutencao = item['ordem__info_solicitacao__tipo_manutencao']
        total_horas = item['total_horas']
        
        if total_horas:
            # Converte para timedelta e depois para horas decimais
            duracao = timedelta(seconds=total_horas.total_seconds())
            horas_decimais = duracao.total_seconds() / 3600  # Total de horas em formato decimal
        else:
            horas_decimais = 0
        
        resultado_formatado.append({
            'tipo_manutencao': tipo_manutencao,
            'total_horas': horas_decimais
        })

    resultado_formatado = sorted(resultado_formatado, key=lambda x: x.get('total_horas', 0), reverse=True)

    # Retorna o resultado em formato JSON para o frontend
    return JsonResponse({'data': resultado_formatado})
