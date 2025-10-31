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

from collections import defaultdict
from io import BytesIO
from datetime import timedelta, datetime, time
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def dashboard(request):

    setores = Setor.objects.all()

    return render(request, 'dashboard.html', {'setores':setores})

def dashboard_predial(request):

    setores = Setor.objects.all()

    return render(request, 'dashboard-predial.html', {'setores':setores})

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
    maquinas_criticas = request.GET.get('maquina-critica', "False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Considera 9 horas de expediente por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    # Filtros base para consultas
    filtros_base = {
        'ordem__area': area
    }
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = maquinas_criticas

    # Buscar as paradas considerando paradas ativas (data_fim nula)
    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,  # Paradas que começaram até o fim do período
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    maquinas_paradas = {}

    for parada in paradas_queryset:
        
        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        # Se data_fim é NULL, considera a parada até o fim do período consultado
        data_fim_parada = parada.data_fim if parada.data_fim else data_fim

        # Ajustar início e fim da parada ao período filtrado
        data_inicio_parada = max(parada.data_inicio, data_inicio)
        data_fim_parada = min(data_fim_parada, data_fim)

        if data_fim_parada <= data_inicio_parada:
            continue  # Paradas fora do período ignoradas

        duracao_total = timedelta()

        dia_atual = data_inicio_parada.date()
        fim_parada = data_fim_parada

        while dia_atual <= fim_parada.date():
            # Define jornada diária (9h): Segunda a Sexta 8:00-17:00, Sábado 8:00-12:00, Domingo sem expediente
            if dia_atual.weekday() < 5:  # Segunda a Sexta
                inicio_jornada = datetime.combine(dia_atual, time(8, 0))
                fim_jornada = datetime.combine(dia_atual, time(17, 0))
            elif dia_atual.weekday() == 5:  # Sábado
                inicio_jornada = datetime.combine(dia_atual, time(8, 0))
                fim_jornada = datetime.combine(dia_atual, time(12, 0))
            else:  # Domingo
                dia_atual += timedelta(days=1)
                continue

            inicio_intersecao = max(data_inicio_parada, inicio_jornada)
            fim_intersecao = min(fim_parada, fim_jornada)

            if fim_intersecao > inicio_intersecao:
                duracao_total += fim_intersecao - inicio_intersecao

            dia_atual += timedelta(days=1)

        # Acumula resultados por máquina
        if codigo_maquina not in maquinas_paradas:
            maquinas_paradas[codigo_maquina] = {'total_paradas': timedelta(), 'quantidade_paradas': 0}

        maquinas_paradas[codigo_maquina]['total_paradas'] += duracao_total
        maquinas_paradas[codigo_maquina]['quantidade_paradas'] += 1

    # Criar lista com totais e quantidades por máquina
    paradas = []
    for codigo, dados in maquinas_paradas.items():
        paradas.append({
            'ordem__maquina__codigo': codigo,
            'total_paradas': dados['total_paradas'],
            'quantidade_paradas': dados['quantidade_paradas'],
        })

    # Garantir que todas as máquinas do filtro estejam na lista, mesmo sem paradas
    filtros_maquinas = {
        'area': area,
    }
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)

    mtbf_dict = {}
    for codigo in todas_maquinas:
        mtbf_dict[codigo] = (0, 0)

    for parada in paradas:
        codigo = parada['ordem__maquina__codigo']
        total_horas = parada['total_paradas'].total_seconds() / 3600
        qtd_paradas = parada['quantidade_paradas']
        mtbf_dict[codigo] = (total_horas, qtd_paradas)

    # Calcular MTBF para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        if qtd_paradas == 0:
            mtbf = None  # Ou definir como 0, ou outro valor conforme regra de negócio
        else:
            mtbf = (tempo_atividade_esperada - tempo_total_paradas) / qtd_paradas
            if mtbf < 0:
                mtbf = 0

        resultados.append({
            'maquina': maquina,
            'mtbf': round(mtbf, 2) if mtbf is not None else None
        })

    resultados = sorted(resultados, key=lambda x: (x['mtbf'] is not None, x['mtbf']), reverse=True)

    return JsonResponse(resultados, safe=False)
    
def exportar_mtbf_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica', "False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Considera 9 horas de expediente por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    # Filtros base para consultas
    filtros_base = {
        'ordem__area': area
    }
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = maquinas_criticas

    # Buscar as paradas considerando paradas ativas (data_fim nula)
    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,  # Paradas que começaram até o fim do período
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    maquinas_paradas = {}

    for parada in paradas_queryset:
        
        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        # Se data_fim é NULL, considera a parada até o fim do período consultado
        data_fim_parada = parada.data_fim if parada.data_fim else data_fim

        # Ajustar início e fim da parada ao período filtrado
        data_inicio_parada = max(parada.data_inicio, data_inicio)
        data_fim_parada = min(data_fim_parada, data_fim)

        if data_fim_parada <= data_inicio_parada:
            continue  # Paradas fora do período ignoradas

        duracao_total = timedelta()

        dia_atual = data_inicio_parada.date()
        fim_parada = data_fim_parada

        while dia_atual <= fim_parada.date():
            # Define jornada diária (9h): Segunda a Sexta 8:00-17:00, Sábado 8:00-12:00, Domingo sem expediente
            if dia_atual.weekday() < 5:  # Segunda a Sexta
                inicio_jornada = datetime.combine(dia_atual, time(8, 0))
                fim_jornada = datetime.combine(dia_atual, time(17, 0))
            elif dia_atual.weekday() == 5:  # Sábado
                inicio_jornada = datetime.combine(dia_atual, time(8, 0))
                fim_jornada = datetime.combine(dia_atual, time(12, 0))
            else:  # Domingo
                dia_atual += timedelta(days=1)
                continue

            inicio_intersecao = max(data_inicio_parada, inicio_jornada)
            fim_intersecao = min(fim_parada, fim_jornada)

            if fim_intersecao > inicio_intersecao:
                duracao_total += fim_intersecao - inicio_intersecao

            dia_atual += timedelta(days=1)

        # Acumula resultados por máquina
        if codigo_maquina not in maquinas_paradas:
            maquinas_paradas[codigo_maquina] = {'total_paradas': timedelta(), 'quantidade_paradas': 0}

        maquinas_paradas[codigo_maquina]['total_paradas'] += duracao_total
        maquinas_paradas[codigo_maquina]['quantidade_paradas'] += 1

    # Criar lista com totais e quantidades por máquina
    paradas = []
    for codigo, dados in maquinas_paradas.items():
        paradas.append({
            'ordem__maquina__codigo': codigo,
            'total_paradas': dados['total_paradas'],
            'quantidade_paradas': dados['quantidade_paradas'],
        })

    # Garantir que todas as máquinas do filtro estejam na lista, mesmo sem paradas
    filtros_maquinas = {
        'area': area,
    }
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)

    mtbf_dict = {}
    for codigo in todas_maquinas:
        mtbf_dict[codigo] = (0, 0)

    for parada in paradas:
        codigo = parada['ordem__maquina__codigo']
        total_horas = parada['total_paradas'].total_seconds() / 3600
        qtd_paradas = parada['quantidade_paradas']
        mtbf_dict[codigo] = (total_horas, qtd_paradas)

    # Calcular MTBF para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        if qtd_paradas == 0:
            mtbf = None  # Ou definir como 0, ou outro valor conforme regra de negócio
        else:
            mtbf = (tempo_atividade_esperada - tempo_total_paradas) / qtd_paradas
            if mtbf < 0:
                mtbf = 0

        resultados.append({
            'maquina': maquina,
            'mtbf': round(mtbf, 2) if mtbf is not None else None
        })

    resultados = sorted(resultados, key=lambda x: (x['mtbf'] is not None, x['mtbf']), reverse=True)

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
    maquinas_criticas = request.GET.get('maquina-critica', "False")
    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area,
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = True

    # --- 1) IDs por máquina (para log e resposta) ---
    exec_ids_map = defaultdict(list)
    ids_qs = Execucao.objects.filter(**filtros, n_execucao__gt=0).values('ordem__maquina__codigo', 'id')
    for row in ids_qs:
        exec_ids_map[row['ordem__maquina__codigo']].append(row['id'])

    # --- 2) Agregações para horas totais e contagem ---
    execucoes = (
        Execucao.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')
        .annotate(
            total_tempo_reparo=Sum('duracao'),
            quantidade_reparos=Count('id')
        )
        .filter(n_execucao__gt=0)
    )

    # Garante todas as máquinas no resultado
    filtros_maquinas = {'area': area}
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)

    # mttr_dict: codigo -> (horas_total, execucoes, ids_list)
    mttr_dict = {codigo: (None, 0, exec_ids_map.get(codigo, [])) for codigo in todas_maquinas}

    for execucao in execucoes:
        codigo = execucao['ordem__maquina__codigo']
        total_segundos = execucao['total_tempo_reparo'].total_seconds() if execucao['total_tempo_reparo'] else 0
        qtd_reparos = execucao['quantidade_reparos']
        horas_total = (total_segundos / 3600) if qtd_reparos > 0 else None
        ids_list = exec_ids_map.get(codigo, [])

        mttr_dict[codigo] = (horas_total, qtd_reparos, ids_list)

        # === LOG ===
        if horas_total is not None and qtd_reparos > 0:
            logger.info(
                f"[MTTR] Maquina={codigo} | Horas_total={horas_total:.2f} | "
                f"Execucoes={qtd_reparos} | Exec_IDs={ids_list}"
            )
        else:
            logger.info(f"[MTTR] Maquina={codigo} | Sem dados no período | Exec_IDs={ids_list}")

    resultados = []
    for maquina, (horas_total, qtd, ids_list) in mttr_dict.items():
        if horas_total is None or qtd == 0:
            mttr_val = 'Sem dados'
            horas_out = None
        else:
            mttr_val = round(horas_total / qtd, 2)
            horas_out = round(horas_total, 2)

        resultados.append({
            'maquina': maquina,
            'mttr': mttr_val,              # horas por reparo
            'horas_total': horas_out,      # horas somadas no período
            'execucoes': qtd,              # quantidade de reparos
            'execucoes_ids': ids_list,     # IDs das execuções
        })

    # Ordena colocando 'Sem dados' no fim
    def chave_ordem(x):
        return x['mttr'] if isinstance(x['mttr'], (int, float)) else -1

    resultados = sorted(resultados, key=chave_ordem, reverse=True)
    return JsonResponse(resultados, safe=False)

def exportar_mttr_maquina(request):
    
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica', "False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    filtros = {
        'data_inicio__gte': data_inicio,
        'data_fim__lte': data_fim,
        'ordem__area': area,
    }
    if setor:
        filtros['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros['ordem__maquina__maquina_critica'] = maquinas_criticas

    execucoes = (
        Execucao.objects.filter(**filtros)
        .annotate(duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField()))
        .values('ordem__maquina__codigo')
        .annotate(
            total_tempo_reparo=Sum('duracao'),
            quantidade_reparos=Count('id')
        )
    )

    # Dicionário inicial com todas máquinas no filtro para garantir todas no resultado
    filtros_maquinas = {'area': area}
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)
    mttr_dict = {codigo: (None, 0) for codigo in todas_maquinas}

    # Preenche com dados de execuções encontradas
    for execucao in execucoes:
        codigo = execucao['ordem__maquina__codigo']
        total_segundos = execucao['total_tempo_reparo'].total_seconds() if execucao['total_tempo_reparo'] else 0
        qtd_reparos = execucao['quantidade_reparos']
        mttr_dict[codigo] = (total_segundos / 3600 if qtd_reparos > 0 else None, qtd_reparos)

    resultados = []
    for maquina, (tempo_horas, qtd) in mttr_dict.items():
        if tempo_horas is None or qtd == 0:
            mttr_val = 'Sem dados'
        else:
            mttr_val = round(tempo_horas / qtd, 2)

        resultados.append({'maquina': maquina, 'mttr': mttr_val})

    # Ordena tratando 'Sem dados' para o fim da lista
    def chave_ordem(x):
        return x['mttr'] if isinstance(x['mttr'], (int, float)) else -1

    resultados = sorted(resultados, key=chave_ordem, reverse=True)

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Tempo de atividade esperada: 9 horas por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    # Filtros base
    filtros_base = {
        'ordem__area': area
    }
    
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = maquinas_criticas

    # ==== BUSCAR E CALCULAR PARADAS (MTBF) COM TRATAMENTO DE data_fim NULL ====
    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,  # Paradas que começam até o fim do período
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    # Processar paradas individualmente para lidar com data_fim NULL
    maquinas_paradas = {}

    for parada in paradas_queryset:
        
        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        # Se data_fim é NULL, considera que a máquina está parada até o fim do período consultado
        data_fim_parada = parada.data_fim if parada.data_fim else data_fim

        # Ajusta data_inicio e data_fim ao período consultado
        data_inicio_parada = max(parada.data_inicio, data_inicio)
        data_fim_parada = min(data_fim_parada, data_fim)

        if data_fim_parada <= data_inicio_parada:
            continue  # ignora paradas fora do período

        # Calcula a duração apenas dentro das 9h/dia
        duracao_total = timedelta()

        dia_atual = data_inicio_parada.date()
        fim_parada = data_fim_parada

        while dia_atual <= fim_parada.date():
            # Define janela de trabalho do dia (9h)
            inicio_jornada = datetime.combine(dia_atual, time(8, 0))  # exemplo: início 08:00
            fim_jornada = datetime.combine(dia_atual, time(17, 0))    # fim 17:00 (9h)

            # Calcula a interseção entre a parada e a jornada
            inicio_intersecao = max(data_inicio_parada, inicio_jornada)
            fim_intersecao = min(fim_parada, fim_jornada)

            if fim_intersecao > inicio_intersecao:
                duracao_total += fim_intersecao - inicio_intersecao

            # Passa para o próximo dia
            dia_atual += timedelta(days=1)

        # Acumula resultados por máquina
        if codigo_maquina not in maquinas_paradas:
            maquinas_paradas[codigo_maquina] = {'total_paradas': timedelta(), 'quantidade_paradas': 0}

        maquinas_paradas[codigo_maquina]['total_paradas'] += duracao_total
        maquinas_paradas[codigo_maquina]['quantidade_paradas'] += 1

    # Build paradas list outside the loop
    paradas = []
    for codigo, dados in maquinas_paradas.items():
        paradas.append({
            'ordem__maquina__codigo': codigo,
            'total_paradas': dados['total_paradas'],
            'quantidade_paradas': dados['quantidade_paradas']
        })

    # Remover cálculo de MTTR - não é mais necessário

    # Organizar os dados das paradas
    mtbf_dict = {}

    # Ensure all machines that match the filter appear (even with zero stops)
    filtros_maquinas = {
        'area': area,
    }
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)
    for codigo in todas_maquinas:
        mtbf_dict[codigo] = (0, 0)

    # Fill with data for machines that had stops
    for parada in paradas:
        codigo = parada['ordem__maquina__codigo']
        total_horas = parada['total_paradas'].total_seconds() / 3600
        qtd_paradas = parada['quantidade_paradas']
        mtbf_dict[codigo] = (total_horas, qtd_paradas)

    # Calcular a disponibilidade para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        # Fórmula simplificada de disponibilidade
        disponibilidade = (tempo_atividade_esperada - tempo_total_paradas) / tempo_atividade_esperada

        resultados.append({
            'maquina': maquina,
            'disponibilidade': disponibilidade * 100,
            'tempo_perfeito': tempo_atividade_esperada,
            'tempo_total_paradas_horas': tempo_total_paradas,
            'qtd_paradas': qtd_paradas
        })

    resultados = sorted(resultados, key=lambda x: x['disponibilidade'], reverse=True)
    
    return JsonResponse(resultados, safe=False)

def exportar_disponibilidade_maquina(request):

    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Tempo de atividade esperada: 9 horas por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    # Filtros base
    filtros_base = {
        'ordem__area': area
    }
    
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = maquinas_criticas

    # ==== BUSCAR E CALCULAR PARADAS (MTBF) COM TRATAMENTO DE data_fim NULL ====
    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,  # Paradas que começam até o fim do período
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    # Processar paradas individualmente para lidar com data_fim NULL
    maquinas_paradas = {}

    for parada in paradas_queryset:

        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        # Se data_fim é NULL, considera que a máquina está parada até o fim do período consultado
        data_fim_parada = parada.data_fim if parada.data_fim else data_fim

        # Ajusta data_inicio e data_fim ao período consultado
        data_inicio_parada = max(parada.data_inicio, data_inicio)
        data_fim_parada = min(data_fim_parada, data_fim)

        if data_fim_parada <= data_inicio_parada:
            continue  # ignora paradas fora do período

        # Calcula a duração apenas dentro das 9h/dia
        duracao_total = timedelta()

        dia_atual = data_inicio_parada.date()
        fim_parada = data_fim_parada

        while dia_atual <= fim_parada.date():
            # Define janela de trabalho do dia (9h)
            inicio_jornada = datetime.combine(dia_atual, time(8, 0))  # exemplo: início 08:00
            fim_jornada = datetime.combine(dia_atual, time(17, 0))    # fim 17:00 (9h)

            # Calcula a interseção entre a parada e a jornada
            inicio_intersecao = max(data_inicio_parada, inicio_jornada)
            fim_intersecao = min(fim_parada, fim_jornada)

            if fim_intersecao > inicio_intersecao:
                duracao_total += fim_intersecao - inicio_intersecao

            # Passa para o próximo dia
            dia_atual += timedelta(days=1)

        # Acumula resultados por máquina
        if codigo_maquina not in maquinas_paradas:
            maquinas_paradas[codigo_maquina] = {'total_paradas': timedelta(), 'quantidade_paradas': 0}

        maquinas_paradas[codigo_maquina]['total_paradas'] += duracao_total
        maquinas_paradas[codigo_maquina]['quantidade_paradas'] += 1

    # Build paradas list outside the loop
    paradas = []
    for codigo, dados in maquinas_paradas.items():
        paradas.append({
            'ordem__maquina__codigo': codigo,
            'total_paradas': dados['total_paradas'],
            'quantidade_paradas': dados['quantidade_paradas']
        })

    # Remover cálculo de MTTR - não é mais necessário

    # Organizar os dados das paradas
    mtbf_dict = {}

    # Ensure all machines that match the filter appear (even with zero stops)
    filtros_maquinas = {
        'area': area,
    }
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)
    for codigo in todas_maquinas:
        mtbf_dict[codigo] = (0, 0)

    # Fill with data for machines that had stops
    for parada in paradas:
        codigo = parada['ordem__maquina__codigo']
        total_horas = parada['total_paradas'].total_seconds() / 3600
        qtd_paradas = parada['quantidade_paradas']
        mtbf_dict[codigo] = (total_horas, qtd_paradas)

    # Calcular a disponibilidade para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        # Fórmula simplificada de disponibilidade
        disponibilidade = (tempo_atividade_esperada - tempo_total_paradas) / tempo_atividade_esperada

        resultados.append({
            'maquina': maquina,
            'disponibilidade': disponibilidade * 100,
            'tempo_perfeito': tempo_atividade_esperada,
            'tempo_total_paradas_horas': tempo_total_paradas,
            'qtd_paradas': qtd_paradas
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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # NOVA LÓGICA baseada em disponibilidade_maquina:
    # - considera paradas com data_fim NULL até o fim do período
    # - computa apenas horas na janela 08:00–17:00 (9h/dia)
    # - inclui máquinas sem paradas com 0 horas

    # Filtros base para paradas
    filtros_base = {
        'ordem__area': area
    }
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = True

    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    totais_por_maquina = {}
    for parada in paradas_queryset:

        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        fim_real = parada.data_fim if parada.data_fim else data_fim
        inicio_real = max(parada.data_inicio, data_inicio)
        fim_real = min(fim_real, data_fim)

        if fim_real <= inicio_real:
            continue

        duracao_total = timedelta()
        dia_atual = inicio_real.date()
        while dia_atual <= fim_real.date():
            inicio_jornada = datetime.combine(dia_atual, time(8, 0))
            fim_jornada = datetime.combine(dia_atual, time(17, 0))

            inicio_inter = max(inicio_real, inicio_jornada)
            fim_inter = min(fim_real, fim_jornada)

            if fim_inter > inicio_inter:
                duracao_total += fim_inter - inicio_inter

            dia_atual += timedelta(days=1)

        totais_por_maquina[codigo_maquina] = totais_por_maquina.get(codigo_maquina, timedelta()) + duracao_total

    # Apenas máquinas com parada (excluir as sem paradas)
    resultado = []
    for codigo, total_td in totais_por_maquina.items():
        total_horas = round(total_td.total_seconds() / 3600, 2)
        if total_horas > 0:
            resultado.append({'maquina': codigo, 'total_horas': total_horas})

    resultado = sorted(resultado, key=lambda x: x['total_horas'], reverse=True)
    return JsonResponse({'data': resultado })

def exportar_maquina_parada_excel(request):
    data_inicio = datetime.strptime(request.GET.get('data-inicial') + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    data_fim = datetime.strptime(request.GET.get('data-final') + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    setor = request.GET.get('setor')
    area = request.GET.get('area')
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # NOVA LÓGICA baseada em disponibilidade_maquina:
    # - considera paradas com data_fim NULL até o fim do período
    # - computa apenas horas na janela 08:00–17:00 (9h/dia)
    # - inclui máquinas sem paradas com 0 horas

    # Filtros base para paradas
    filtros_base = {
        'ordem__area': area
    }
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = True

    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    totais_por_maquina = {}
    for parada in paradas_queryset:
        
        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue
        
        codigo_maquina = parada.ordem.maquina.codigo

        fim_real = parada.data_fim if parada.data_fim else data_fim
        inicio_real = max(parada.data_inicio, data_inicio)
        fim_real = min(fim_real, data_fim)

        if fim_real <= inicio_real:
            continue

        duracao_total = timedelta()
        dia_atual = inicio_real.date()
        while dia_atual <= fim_real.date():
            inicio_jornada = datetime.combine(dia_atual, time(8, 0))
            fim_jornada = datetime.combine(dia_atual, time(17, 0))

            inicio_inter = max(inicio_real, inicio_jornada)
            fim_inter = min(fim_real, fim_jornada)

            if fim_inter > inicio_inter:
                duracao_total += fim_inter - inicio_inter

            dia_atual += timedelta(days=1)

        totais_por_maquina[codigo_maquina] = totais_por_maquina.get(codigo_maquina, timedelta()) + duracao_total

    # Apenas máquinas com parada (excluir as sem paradas)
    resultado = []
    for codigo, total_td in totais_por_maquina.items():
        total_horas = round(total_td.total_seconds() / 3600, 2)
        if total_horas > 0:
            resultado.append({'maquina': codigo, 'total_horas': total_horas})

    resultado = sorted(resultado, key=lambda x: x['total_horas'], reverse=True)

    df = pd.DataFrame(resultado)

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

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
    data_inicial = request.GET.get('data-inicial')
    data_final = request.GET.get('data-final')
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(data_inicio__gte=data_inicial, data_fim__lte=data_final, data_fim__isnull=False, ordem__area=area, ordem__maquina__maquina_critica=maquinas_criticas).annotate(
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
    data_inicial = request.GET.get('data-inicial')
    data_final = request.GET.get('data-final')
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(data_inicio__gte=data_inicial, data_fim__lte=data_final, data_fim__isnull=False, ordem__area=area, ordem__maquina__maquina_critica=maquinas_criticas).annotate(
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
    maquinas_criticas = request.GET.get('maquina-critica',"False")
    data_inicial = request.GET.get('data-inicial')
    data_final = request.GET.get('data-final')

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(
        data_inicio__gte=data_inicial,
        data_fim__lte=data_final,
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
    maquinas_criticas = request.GET.get('maquina-critica',"False")
    data_inicial = request.GET.get('data-inicial')
    data_final = request.GET.get('data-final')

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    resultado = Execucao.objects.filter(
        data_inicio__gte=data_inicial,
        data_fim__lte=data_final,
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
    maquinas_criticas = request.GET.get('maquina-critica',"False")

    maquinas_criticas = maquinas_criticas.lower() == 'true'

    # Tempo de atividade esperada: 9 horas por dia
    dias_mes = (data_fim - data_inicio).days + 1
    tempo_atividade_esperada = dias_mes * 9  # Total de horas esperadas no mês

    # Filtros base
    filtros_base = {
        'ordem__area': area
    }
    
    if setor:
        filtros_base['ordem__setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_base['ordem__maquina__maquina_critica'] = maquinas_criticas

    # ==== BUSCAR E CALCULAR PARADAS (MTBF) COM TRATAMENTO DE data_fim NULL ====
    filtros_paradas = filtros_base.copy()
    filtros_paradas.update({
        'data_inicio__lte': data_fim,  # Paradas que começam até o fim do período
    })

    paradas_queryset = MaquinaParada.objects.filter(**filtros_paradas).select_related('ordem__maquina')

    # Processar paradas individualmente para lidar com data_fim NULL
    maquinas_paradas = {}

    for parada in paradas_queryset:
        
        if not parada.ordem or not parada.ordem.maquina:
            # Ignora essa parada pois faltam dados obrigatórios
            continue

        codigo_maquina = parada.ordem.maquina.codigo

        # Se data_fim é NULL, considera que a máquina está parada até o fim do período consultado
        data_fim_parada = parada.data_fim if parada.data_fim else data_fim

        # Ajusta data_inicio e data_fim ao período consultado
        data_inicio_parada = max(parada.data_inicio, data_inicio)
        data_fim_parada = min(data_fim_parada, data_fim)

        if data_fim_parada <= data_inicio_parada:
            continue  # ignora paradas fora do período

        # Calcula a duração apenas dentro das 9h/dia
        duracao_total = timedelta()

        dia_atual = data_inicio_parada.date()
        fim_parada = data_fim_parada

        while dia_atual <= fim_parada.date():
            # Define janela de trabalho do dia (9h)
            inicio_jornada = datetime.combine(dia_atual, time(8, 0))  # exemplo: início 08:00
            fim_jornada = datetime.combine(dia_atual, time(17, 0))    # fim 17:00 (9h)

            # Calcula a interseção entre a parada e a jornada
            inicio_intersecao = max(data_inicio_parada, inicio_jornada)
            fim_intersecao = min(fim_parada, fim_jornada)

            if fim_intersecao > inicio_intersecao:
                duracao_total += fim_intersecao - inicio_intersecao

            # Passa para o próximo dia
            dia_atual += timedelta(days=1)

        # Acumula resultados por máquina
        if codigo_maquina not in maquinas_paradas:
            maquinas_paradas[codigo_maquina] = {'total_paradas': timedelta(), 'quantidade_paradas': 0}

        maquinas_paradas[codigo_maquina]['total_paradas'] += duracao_total
        maquinas_paradas[codigo_maquina]['quantidade_paradas'] += 1

    # Build paradas list outside the loop
    paradas = []
    for codigo, dados in maquinas_paradas.items():
        paradas.append({
            'ordem__maquina__codigo': codigo,
            'total_paradas': dados['total_paradas'],
            'quantidade_paradas': dados['quantidade_paradas']
        })

    # Remover cálculo de MTTR - não é mais necessário

    # Organizar os dados das paradas
    mtbf_dict = {}

    # Ensure all machines that match the filter appear (even with zero stops)
    filtros_maquinas = {
        'area': area,
    }
    if setor:
        filtros_maquinas['setor_id'] = int(setor)
    if maquinas_criticas:
        filtros_maquinas['maquina_critica'] = True

    todas_maquinas = Maquina.objects.filter(**filtros_maquinas).values_list('codigo', flat=True)
    for codigo in todas_maquinas:
        mtbf_dict[codigo] = (0, 0)

    # Fill with data for machines that had stops
    for parada in paradas:
        codigo = parada['ordem__maquina__codigo']
        total_horas = parada['total_paradas'].total_seconds() / 3600
        qtd_paradas = parada['quantidade_paradas']
        mtbf_dict[codigo] = (total_horas, qtd_paradas)

    # Calcular a disponibilidade para cada máquina
    resultados = []
    for maquina, (tempo_total_paradas, qtd_paradas) in mtbf_dict.items():
        # Fórmula simplificada de disponibilidade
        disponibilidade = (tempo_atividade_esperada - tempo_total_paradas) / tempo_atividade_esperada

        resultados.append({
            'maquina': maquina,
            'disponibilidade': disponibilidade * 100,
            'tempo_perfeito': tempo_atividade_esperada,
            'tempo_total_paradas_horas': tempo_total_paradas,
            'qtd_paradas': qtd_paradas
        })

    resultados = sorted(resultados, key=lambda x: x['disponibilidade'], reverse=True)
    
    disponibilidade_geral_media = sum(x['disponibilidade'] for x in resultados) / len(resultados) if resultados else 0

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
