from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils.timezone import now
from django.db.models import Sum, F, ExpressionWrapper, DurationField

from solicitacao.models import Solicitacao
from execucao.models import Execucao

def dashboard_predial(request):
    return render(request, 'dashboard.html')

# 1. Ordens Abertas e Finalizadas por Mês
def ordens_por_mes(request, area):

    # Agrupa por mês e conta as solicitações abertas
    dados = (
        Solicitacao.objects.filter(data_abertura__year=now().year, area=area)
        .annotate(mes=TruncMonth('data_abertura'))
        .values('mes')
        .annotate(quantidade=Count('id'))
        .order_by('mes')
    )

    ordens_finalizadas = (
        Execucao.objects.filter(ultima_atualizacao__year=now().year, ordem__area=area)
        .annotate(mes=TruncMonth('ultima_atualizacao'))
        .values('mes')
        .annotate(quantidade=Count('id'))
        .order_by('mes')
    )

    # Prepara os dados para retornar como JSON
    labels = [dado['mes'].strftime('%B') for dado in dados]  # Nomes dos meses
    valores = [dado['quantidade'] for dado in dados]  # Quantidade de ordens por mês
    ordens_finalizadas = [dado['quantidade'] for dado in ordens_finalizadas]

    return JsonResponse({'labels': labels, 'valores': valores, 'ordens_finalizadas': ordens_finalizadas})

# 2. Setor que Mais Solicita
def setor_mais_solicita(request, area):

    dados = (
        Execucao.objects.filter(ordem__area=area).values('ordem__setor__nome')
        .annotate(quantidade=Count('id'))
        .order_by('-quantidade')
    )

    labels = [dado['ordem__setor__nome'] for dado in dados]
    valores = [dado['quantidade'] for dado in dados]

    return JsonResponse({
        'labels': labels,
        'valores': valores
    })

# 3. Por máquina
def horas_servico_por_maquina(request, area):
    # Calcula a diferença entre data_fim e data_inicio e soma para cada máquina
    execucoes = (
        Execucao.objects
        .filter(data_fim__isnull=False, ordem__area=area)  # Filtra apenas as execuções finalizadas
        .annotate(
            duracao=ExpressionWrapper(F('data_fim') - F('data_inicio'), output_field=DurationField())
        )
        .values('ordem__maquina__codigo', 'ordem__maquina__descricao')
        .annotate(total_horas=Sum('duracao'))
        .order_by('ordem__maquina__codigo')
    )

    # Prepara os dados para o gráfico
    horas_por_maquina = [
        {
            'maquina_codigo': execucao['ordem__maquina__codigo'],
            'maquina_descricao': execucao['ordem__maquina__descricao'],
            'total_horas': execucao['total_horas'].total_seconds() / 3600  # Converte para horas
        }
        for execucao in execucoes
    ]

    return JsonResponse({'horas_por_maquina': horas_por_maquina})

