from django.http import JsonResponse,HttpResponse
from django.db.models import Sum, Count, F, ExpressionWrapper, DurationField, Avg, Min, Max, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils.timezone import now, timedelta
from django.db.models import Sum, F, ExpressionWrapper, DurationField, OuterRef, Subquery
from django.utils.functional import SimpleLazyObject
from django.utils import timezone
from django.db.models.functions import TruncDate

from solicitacao.models import Solicitacao
from execucao.models import Execucao, MaquinaParada, InfoSolicitacao
from cadastro.models import Maquina, Setor
from preventiva.models import PlanoPreventiva

from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd

def dashboard(request):

    setores = Setor.objects.all()

    return render(request, 'dashboard.html', {'setores':setores})

# Gráficos

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
        -Segunda à Sexta -- 8:00 às 18:00
        -Sábado -- 8:00 às 12:00
        -Domingo -- sem expediente
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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'



    # Tempo de atividade esperada: 9 horas por dia
    # dias_mes = (data_fim - data_inicio).days + 1
    # tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês
    tempo_atividade_esperada = tempo_util(data_inicio,data_fim)/3600

    filtros = {
            'data_inicio__gte': data_inicio,
            'data_fim__lte': data_fim,
            'ordem__area': area,
        }
    if setor:
        filtros['ordem__setor_id'] = int(setor)

    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    # paradas = (
    #     MaquinaParada.objects.filter(**filtros)
    #     .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
    #     .values('ordem__maquina__codigo') # Agrupa pelo codigo da máquina
    #     .annotate(
    #         total_paradas=Sum('duracao'),  # Soma das durações das paradas
    #         quantidade_paradas=Count('id')  # Contagem de paradas
    #     )
    # )

    # Buscar as paradas do mês atual e calcular a duração de cada uma
    paradas = (
        MaquinaParada.objects.filter(**filtros)
        .values('ordem__maquina__codigo')
        .annotate(
            quantidade_paradas=Count('id')
        ) # Agrupa pelo codigo da máquina
    )

    print(paradas)
    
    # Preparar os dados para o JSON
    resultados = []
    
    for parada in paradas:
        filtros['ordem__maquina__codigo'] = parada['ordem__maquina__codigo']
        total_duracao = sum(tempo_util(p.data_inicio, p.data_fim) for p in MaquinaParada.objects.filter(**filtros))
        tempo_total_paradas_horas = total_duracao / 3600
        # tempo_total_paradas_horas = parada['total_paradas'].total_seconds() / 3600  # Converter para horas
        quantidade_paradas = parada['quantidade_paradas']

        # Cálculo do MTBF
        mtbf = (tempo_atividade_esperada - tempo_total_paradas_horas) / quantidade_paradas
        # print("Tempo atividade esperada: ",tempo_atividade_esperada)
        # print("Tempo parada: ",tempo_total_paradas_horas)
        # print("Quantidade de paradas: ",quantidade_paradas)
        # print("mtbf: ",mtbf)

        resultados.append({
            'maquina': parada['ordem__maquina__codigo'],
            'mtbf': round(mtbf, 2)
        })

    resultados = sorted(resultados, key=lambda x: x['mtbf'], reverse=True)

    return JsonResponse(resultados, safe=False)

def exportar_mtbf_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

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
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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

    df = pd.DataFrame(resultados)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Mtbf Máquina')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="mtbf_maquina.xlsx"'
    return response

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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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

def exportar_mttr_maquina(request):
    
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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

    df = pd.DataFrame(resultados)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Mttr Máquina')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="mttr_maquina.xlsx"'
    return response

def disponibilidade_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

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
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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

def exportar_disponibilidade_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

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
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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
    
    df = pd.DataFrame(resultados)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Disponibilidade Máquina')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="disponibilidade_maquina.xlsx"'
    return response

def ordens_prazo(request):
    """
    Retorna um indicador de ordens finalizadas dentro e fora do prazo.
    """
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'status_andamento': 'finalizada',
        'area': area
    }
    if setor:
        filtros['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

    # Subquery para pegar a última execução de cada solicitação
    ultima_execucao_subquery = (
        Execucao.objects.filter(ordem=OuterRef('pk'), ordem__area=area)
        .order_by('-data_fim')
        .values('data_fim')[:1]
    )

    # Filtra as solicitações que foram finalizadas
    solicitacoes = Solicitacao.objects.filter(**filtros).exclude(status='rejeitar')

    # Anota a última data de execução (sem o tempo) para cada solicitação
    solicitacoes = solicitacoes.annotate(
        ultima_data_fim=TruncDate(Subquery(ultima_execucao_subquery)),  # Trunca para trabalhar só com a data
    )

    # Calcula as ordens dentro e fora do prazo
    dentro_do_prazo = solicitacoes.filter(
        ultima_data_fim__lte=F('programacao')  # Inclui datas menores ou iguais
    ).count()

    fora_do_prazo = solicitacoes.filter(
        ultima_data_fim__gt=F('programacao')  # Inclui somente datas maiores
    ).count()

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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'solicitacao__status_andamento': 'finalizada',
        'solicitacao__data_abertura__gte': data_inicio,
        'solicitacao__data_abertura__lte':data_fim,
        'solicitacao__area':area
    }
    if setor:
        filtros['solicitacao__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['solicitacao__maquina__maquina_critica'] = maquinas_criticas

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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'ordem__area': area
    }

    # Adiciona o filtro para data_fim, mas permite que ela seja NULL para o cálculo posterior
    filtros['data_fim__lte'] = data_fim

    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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
        # .order_by('-total_duracao')
    )
    
    for maq in total_por_maquina:
        filtros['ordem__maquina__codigo'] = maq['ordem__maquina__codigo']
        total_duracao = sum(tempo_util(p.data_inicio, p.data_fim) for p in MaquinaParada.objects.filter(**filtros))
        maq['total_duracao'] = total_duracao / 3600 if total_duracao else 0
    # Converter o resultado para uma lista de dicionários com as durações em horas
    resultado = [
        {
            'maquina': item['ordem__maquina__codigo'],
            # 'total_horas': item['total_duracao'].total_seconds() / 3600 if item['total_duracao'] else 0
            'total_horas': item['total_duracao']
        }
        for item in total_por_maquina
    ]

    return JsonResponse({'data': resultado })

def exportar_maquina_parada_excel(request):
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'ordem__area': area
    }

    filtros['data_fim__lte'] = data_fim

    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    # Obter os dados
    total_por_maquina = (
        MaquinaParada.objects
        .filter(**filtros)
        .annotate(
            data_fim_real=Coalesce('data_fim', Value(timezone.now())),
            duracao=ExpressionWrapper(
                F('data_fim_real') - F('data_inicio'), output_field=DurationField()
            )
        )
        .values('ordem__maquina__codigo')
        .annotate(total_duracao=Sum('duracao'))
        .order_by('-total_duracao')
    )

    # Converter os dados em um DataFrame do pandas
    dados = [
        {
            'Máquina': item['ordem__maquina__codigo'],
            'Total de Horas': round(item['total_duracao'].total_seconds() / 3600, 2) if item['total_duracao'] else 0
        }
        for item in total_por_maquina
    ]
    df = pd.DataFrame(dados)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Máquinas Paradas')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="maquinas_paradas.xlsx"'
    return response

def solicitacao_setor(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_abertura__gte': data_inicio,
        'data_abertura__lte': data_fim,
        'status':'aprovar',
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

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

def exportar_solicitacao_setor(request):
    
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_abertura__gte': data_inicio,
        'data_abertura__lte': data_fim,
        'status':'aprovar',
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    resultado = (
        Solicitacao.objects
        .filter(**filtros)
        .values('setor__nome')  # Agrupar pelo nome do setor
        .annotate(total=Count('id'))  # Contar as solicitações por setor
        .order_by('setor__nome')  # Ordenar por nome do setor (opcional)

    )

    data = list(resultado)  # Converte o QuerySet em uma lista de dicionários

    data = sorted(data, key=lambda x: x['total'], reverse=True)

    df = pd.DataFrame(data)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Solicitação por setor')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="solicitacao_setor.xlsx"'
    return response

# Cards

def quantidade_abertura_ordens(request):

    """dentro do mês"""

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_abertura__range':[data_inicio,data_fim],
        'area':area
    }
    if setor:
        filtros['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

    ordens = Solicitacao.objects.filter(**filtros).exclude(status='rejeitar').count()

    return JsonResponse({'data':ordens})

def quantidade_finalizada(request):

    """dentro do mês"""

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'status': 'finalizada',
        'data_fim__range': [data_inicio, data_fim],
        'ordem__area':area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    ordens = Execucao.objects.filter(**filtros).count()

    return JsonResponse({'data':ordens})

def quantidade_aguardando_material(request):

    """Geral sem filtro"""

    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'status_andamento': 'aguardando_material',
        'area': area
    }

    if setor:
        filtros['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

    ordens = Solicitacao.objects.filter(**filtros).count()

    return JsonResponse({'data':ordens})

def quantidade_atrasada(filtros):

    if filtros is None:
        filtros = {}

    data_limite = timezone.now()  # ou datetime.date(2024, 11, 1) se desejar uma data fixa

    # Filtra as solicitações atrasadas e conta
    solicitacoes = Solicitacao.objects.filter(
        **filtros,
        programacao__isnull=False,
        programacao__lt=data_limite
    ).exclude(
        Q(status='rejeitar') | Q(status_andamento='finalizada')
    ).count()

    return solicitacoes

def quantidade_atrasada_view(request):

    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Define os filtros para a solicitação
    filtros={'area':area}
    if setor:
        filtros['setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

    fora_do_prazo = quantidade_atrasada(filtros)

    return JsonResponse({'data': fora_do_prazo})

def quantidade_em_execucao(request):

    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Define os filtros para a solicitação
    filtros = {'area': area, 'status_andamento': 'em_execucao', 'status': 'aprovar'}

    if setor:
        filtros['setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

    ordens = Solicitacao.objects.filter(**filtros).count()

    return JsonResponse({'data':ordens})

def tempo_medio_finalizar(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Define os filtros para a solicitação
    filtros = {'status': 'finalizada',
                'ordem__status':'aprovar',
                'ordem__data_abertura__gte':data_inicio,
                'data_fim__lte':data_fim,
                'ordem__area':area}
    
    if setor:
        filtros['ordem__setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Define os filtros para a solicitação
    filtros = {'data_abertura__gte': data_inicio,
                'data_abertura__lte':data_fim,
                'area':area,
                'status':'aprovar'
    }    
    
    if setor:
        filtros['setor_id'] = int(setor)  # Aplica o filtro de setor, se fornecido
    if maquinas_criticas:
        filtros['maquina__maquina_critica'] = maquinas_criticas

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
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(data_fim__isnull=False, ordem__area=area, ordem__maquina__maquina_critica=maquinas_criticas).annotate(
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

def exportar_horas_trabalhadas_setor(request):
    
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(data_fim__isnull=False, ordem__area=area, ordem__maquina__maquina_critica=maquinas_criticas).annotate(
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

    df = pd.DataFrame(resultado_formatado)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Horas trabalhadas por setor')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="horas_trabalhadas_setor.xlsx"'
    return response

def horas_trabalhadas_tipo(request):

    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(
        data_fim__isnull=False,
        ordem__info_solicitacao__tipo_manutencao__isnull=False,
        ordem__area=area,
        ordem__maquina__maquina_critica=maquinas_criticas
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

def exportar_horas_trabalhadas_tipo(request):
    
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(
        data_fim__isnull=False,
        ordem__info_solicitacao__tipo_manutencao__isnull=False,
        ordem__area=area,
        ordem__maquina__maquina_critica=maquinas_criticas
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

    df = pd.DataFrame(resultado_formatado)

    # Criar o arquivo Excel na memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Horas trabalhadas por tipo')

    # Configurar a resposta para download
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="horas_trabalhadas_tipo.xlsx"'
    return response

def disponibilidade_geral(request):
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',False)

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Filtros básicos
    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    # Obtém todas as máquinas e calcula o tempo de atividade esperada por máquina
    maquinas = MaquinaParada.objects.filter(**filtros).values_list('ordem__maquina', flat=True).distinct()

    tempo_atividade_esperada = 0
    for maquina in maquinas:
        dias_maquina = MaquinaParada.objects.filter(ordem__maquina=maquina, **filtros) \
            .annotate(dias=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField())) \
            .aggregate(total_dias=Sum('dias'))['total_dias']
        if dias_maquina:
            tempo_atividade_esperada += (dias_maquina.total_seconds() / 3600) * 9  # 9 horas por dia

    # Calcular total de tempo de paradas
    paradas_total = (
        MaquinaParada.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .aggregate(total_paradas=Sum('duracao'))['total_paradas']
    ) or timedelta()

    # Calcular total de tempo de reparos
    reparos_total = (
        Execucao.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .aggregate(total_reparos=Sum('duracao'))['total_reparos']
    ) or timedelta()

    # Convertendo timedelta para horas
    paradas_horas = paradas_total.total_seconds() / 3600
    reparos_horas = reparos_total.total_seconds() / 3600

    # Calcular disponibilidade geral média
    tempo_disponivel = tempo_atividade_esperada - paradas_horas

    disponibilidade_geral_media = (
        (tempo_disponivel / (tempo_disponivel + reparos_horas)) * 100 if tempo_disponivel + reparos_horas > 0 else 0
    )

    return JsonResponse({'data': round(disponibilidade_geral_media, 2)})


#Função à parte de chamadas de requisições
def tempo_util(data_inicio, data_fim):

    '''
        Função para calcular somente as horas de expediente e 
        evitar erros de cálculo no funcionamento das máquinas
    '''
    # Inicializar a quantidade de horas trabalhadas
    if data_fim is None:
        return 0
    horas_trabalhadas = timedelta()
    # print("Data inicio: ",data_inicio)
    # print("Data fim: ",data_fim)

    # Loop para iterar sobre cada dia no intervalo
    current_day = data_inicio
    
    while current_day <= data_fim:
        if current_day.weekday() < 5:  # Segunda a sexta (0-4)
            # Horário de trabalho de 08:00 às 18:00
            start_of_day = current_day.replace(hour=8, minute=0, second=0)
            end_of_day = current_day.replace(hour=18, minute=0, second=0)
            # Ajustar caso a data de início ou final esteja fora do intervalo
            start_of_day = max(start_of_day, data_inicio)
            end_of_day = min(end_of_day, data_fim)
            if start_of_day < end_of_day:
                horas_trabalhadas += end_of_day - start_of_day
        elif current_day.weekday() == 5:  # Sábado (5)
            # Horário de trabalho de 08:00 às 12:00
            start_of_day = current_day.replace(hour=8, minute=0, second=0)
            end_of_day = current_day.replace(hour=12, minute=0, second=0)
            # Ajustar caso a data de início ou final esteja fora do intervalo
            start_of_day = max(start_of_day, data_inicio)
            end_of_day = min(end_of_day, data_fim)
            if start_of_day < end_of_day:
                horas_trabalhadas += end_of_day - start_of_day

        # Avançar para o próximo dia
        current_day += timedelta(days=1)
    # print("Horas trabalhadas:" ,horas_trabalhadas)
    # print('-----------------')
    # Retornar o total de horas trabalhadas em segundos
    return horas_trabalhadas.total_seconds()
