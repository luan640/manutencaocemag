from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.forms import formset_factory
from django.db.models import OuterRef, Subquery, Value, IntegerField, Q, Count
from django.utils.timezone import datetime, timedelta, now

from .models import PlanoPreventiva, TarefaPreventiva, SolicitacaoPreventiva
from .forms import PlanoPreventivaForm, TarefaPreventivaForm, SolicitacaoPreventivaForm, TarefaPreventivaFormSet
from cadastro.models import Maquina
from solicitacao.models import Solicitacao
from execucao.models import Execucao

from datetime import date, timedelta

def criar_plano_preventiva(request, pk_maquina):
    maquina = get_object_or_404(Maquina, pk=pk_maquina)  # Obtém a máquina específica
    area_maquina = maquina.area

    if request.method == 'POST':
        print(request.POST)
        # Passa a máquina para o formulário, mas não permite que o usuário a edite
        plano_form = PlanoPreventivaForm(request.POST)
        
        if plano_form.is_valid():
            plano = plano_form.save(commit=False)  # Não salva ainda para associar a máquina
            plano.maquina = maquina  # Associa a máquina ao plano
            plano.area = area_maquina
            plano.save()  # Agora salva o plano com a máquina associada

            # Processa as tarefas
            tarefas_data = []
            for key in request.POST:
                if key.startswith('tarefas'):
                    parts = key.split('[')
                    index = int(parts[1].split(']')[0])
                    field = parts[2].split(']')[0]

                    while len(tarefas_data) <= index:
                        tarefas_data.append({})

                    tarefas_data[index][field] = request.POST[key]

            # Cria as tarefas associadas ao plano
            for tarefa in tarefas_data:
                descricao = tarefa.get('descricao')
                responsabilidade = tarefa.get('responsabilidade')

                if descricao and responsabilidade:
                    TarefaPreventiva.objects.create(
                        plano=plano,
                        descricao=descricao,
                        responsabilidade=responsabilidade
                    )

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': plano_form.errors})

    # Renderiza o formulário, associando-o à máquina
    return render(request, 'plano/add.html', {
        'plano_form': PlanoPreventivaForm(),
        'maquina': maquina,
    })

def criar_tarefa_preventiva(request):
    if request.method == 'POST':
        form = TarefaPreventivaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('list_preventivas')
    else:
        form = TarefaPreventivaForm()
    return render(request, 'sua_template.html', {'form': form})

def criar_solicitacao_preventiva(request):
    if request.method == 'POST':
        form = SolicitacaoPreventivaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('list_preventivas')
    else:
        form = SolicitacaoPreventivaForm()
    return render(request, 'sua_template.html', {'form': form})

def list_preventivas(request):
    area = request.GET.get('area')  # Obtém o parâmetro 'area' da query string
    maquina = request.GET.get('maquina')  # Captura o filtro de Máquina
    plano = request.GET.get('plano')  # Captura o filtro de Plano

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        draw = int(request.GET.get('draw', 0))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))

        maquinas_queryset = Maquina.objects.filter(area=area)

        # Ordenação
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_dir = request.GET.get('order[0][dir]', 'asc')
        
        # Mapeamento do índice da coluna para o campo correspondente no banco de dados
        columns = [
            'maquina__codigo',  # ou o campo correto relacionado à máquina
            'nome',
            'descricao',
            'periodicidade',
            'abertura_automatica',
        ]
        
        order_column = columns[order_column_index]

        if order_dir == 'desc':
            order_column = '-' + order_column

        # Filtrando as preventivas (se houver busca)
        search_value = request.GET.get('search[value]', '')

        preventivas = PlanoPreventiva.objects.filter(area=area, ativo=True)

        # Filtros por Máquina e Plano
        if maquina:
            preventivas = preventivas.filter(maquina__codigo=maquina)
        if plano:
            preventivas = preventivas.filter(nome__icontains=plano)

        # Busca global (campo de pesquisa do DataTables)
        if search_value:
            preventivas = preventivas.filter(
                nome__icontains=search_value
            )

        # Aplicando ordenação
        preventivas = preventivas.order_by(order_column)

        # Paginação
        paginator = Paginator(preventivas, length)
        preventivas_page = paginator.get_page(start // length + 1)

        data = []
        for preventiva in preventivas_page:
            data.append({
                'id': preventiva.pk,
                'maquina': str(preventiva.maquina),
                'nome': preventiva.nome,
                'descricao': preventiva.descricao,
                'periodicidade': preventiva.periodicidade,
                'abertura_automatica': 'Sim' if preventiva.abertura_automatica else 'Não',
            })
        
        maquinas = []
        for maquina_obj in maquinas_queryset:
            maquinas.append({
                'id': maquina_obj.pk,
                'codigo': maquina_obj.codigo,
                'nome': maquina_obj.descricao,
            })

        return JsonResponse({
            'draw': draw,
            'recordsTotal': paginator.count,
            'recordsFiltered': paginator.count,
            'data': data,
            'maquinas': maquinas,
        })

    return render(request, 'visualizacao/list.html')

def get_maquinas_preventiva(request):
    """
    Retorna uma lista paginada de máquinas associadas a planos de preventiva ativos,
    com suporte a busca por código ou descrição.
    """

    # Obtém os parâmetros da requisição
    search = request.GET.get('search', '').strip()  # Termo de busca
    page = int(request.GET.get('page', 1))  # Página atual (padrão é 1)
    per_page = int(request.GET.get('per_page', 10))  # Itens por página (padrão é 10)

    # Filtra as máquinas que possuem planos de preventiva ativos
    maquinas_query = Maquina.objects.filter(
        planos_preventiva__ativo=True  # Apenas máquinas com planos de preventiva ativos
    ).distinct()  # Remove duplicatas caso uma máquina esteja associada a múltiplos planos

    # Aplica o filtro de busca, se necessário
    if search:
        maquinas_query = maquinas_query.filter(
            Q(codigo__icontains=search) | Q(descricao__icontains=search)
        ).order_by('codigo')

    # Paginação
    paginator = Paginator(maquinas_query, per_page)
    maquinas_page = paginator.get_page(page)

    # Monta os resultados paginados no formato esperado pelo Select2
    data = {
        'results': [
            {'id': maquina.codigo, 'text': f"{maquina.codigo} - {maquina.descricao}"} for maquina in maquinas_page
        ],
        'pagination': {
            'more': maquinas_page.has_next()  # Indica se há mais páginas disponíveis
        },
    }

    return JsonResponse(data)

def editar_plano_preventiva(request, pk):
    plano = get_object_or_404(PlanoPreventiva, pk=pk)

    if request.method == 'POST':
        plano_form = PlanoPreventivaForm(request.POST, instance=plano)

        if plano_form.is_valid():
            plano = plano_form.save()

            # Processar exclusão das tarefas existentes
            tarefas_para_excluir = request.POST.getlist('tarefas_excluir')
            if tarefas_para_excluir:
                TarefaPreventiva.objects.filter(id__in=tarefas_para_excluir, plano=plano).delete()

            # Atualizar tarefas existentes
            tarefas_existentes = TarefaPreventiva.objects.filter(plano=plano)
            for tarefa in tarefas_existentes:
                descricao = request.POST.get(f'tarefa_{tarefa.id}_descricao')
                responsabilidade = request.POST.get(f'tarefa_{tarefa.id}_responsabilidade')
                
                if descricao and responsabilidade:
                    tarefa.descricao = descricao
                    tarefa.responsabilidade = responsabilidade
                    tarefa.save()

            # Adicionar novas tarefas
            tarefas_novas = []
            for key in request.POST:
                if key.startswith('tarefas_novas'):
                    parts = key.split('[')
                    index = int(parts[1].split(']')[0])
                    field = parts[2].split(']')[0]

                    while len(tarefas_novas) <= index:
                        tarefas_novas.append({})

                    tarefas_novas[index][field] = request.POST[key]

            for tarefa in tarefas_novas:
                descricao = tarefa.get('descricao')
                responsabilidade = tarefa.get('responsabilidade')

                if descricao and responsabilidade:
                    TarefaPreventiva.objects.create(
                        plano=plano,
                        descricao=descricao,
                        responsabilidade=responsabilidade
                    )

            # Retorna uma resposta JSON indicando sucesso
            return JsonResponse({'success': True, 'redirect_url': '/preventiva'})
        else:
            # Retorna uma resposta JSON com os erros do formulário
            errors = plano_form.errors
            return JsonResponse({'success': False, 'errors': errors}, status=400)

    else:
        plano_form = PlanoPreventivaForm(instance=plano)
        tarefas = TarefaPreventiva.objects.filter(plano=plano)
    
    return render(request, 'plano/edit.html', {
        'plano_form': plano_form,
        'tarefas': tarefas,
    })

def ordens_programadas(request,area):

    ordens = Solicitacao.objects.filter(
        programacao__isnull=False,
        area=area
    ).exclude(status_andamento='finalizada')

    today = datetime.today().date()  # Data atual sem o componente de hora

    data = []
    for ordem in ordens:
        data.append({
            'title': f'#{ordem.pk} - {ordem.maquina}',
            'start': ordem.programacao.strftime('%Y-%m-%d'),
            'description': ordem.descricao,
            'setor': ordem.setor.nome,
            'planejada': ordem.planejada,
            'atrasada': today > ordem.programacao,  # Verifica se a ordem está atrasada
            'textColor': 'black'
        })

    return JsonResponse(data, safe=False)

def programacao(request,area):

    return render(request, 'visualizacao/calendar.html', {'area':area})

def planejamento_anual(request):

    return render(request, 'plano/52semanas.html')

def calcular_manutencoes_semanais(request):
    """
    Calcula as manutenções planejadas por semana até o final do ano com base na periodicidade.
    Retorna um JSON com as semanas e os planos por máquina.
    """

    # Data de hoje e último dia do ano
    hoje = datetime.today()
    hoje = datetime(hoje.year, 1, 1)
    ultimo_dia_ano = datetime(hoje.year, 12, 31)

    # Inicializar lista para armazenar as manutenções por semana
    semanas = []

    # Calcular as semanas até o final do ano
    semana_atual = hoje - timedelta(days=hoje.weekday())  # Início da semana atual (segunda-feira)
    while semana_atual <= ultimo_dia_ano:
        semanas.append({
            'inicio': semana_atual.strftime('%Y-%m-%d'),
            'fim': (semana_atual + timedelta(days=6)).strftime('%Y-%m-%d'),
            'manutencoes': []  # Manutenções a serem preenchidas
        })
        semana_atual += timedelta(days=7)  # Avança para a próxima semana

    # Iterar sobre todos os planos preventivos e calcular as execuções futuras
    planos = PlanoPreventiva.objects.all()
    for plano in planos:
        proxima_data = hoje  # Inicia hoje e calcula as próximas execuções
        while proxima_data <= ultimo_dia_ano:
            # Encontrar a semana correspondente à data calculada
            for semana in semanas:
                inicio = datetime.strptime(semana['inicio'], '%Y-%m-%d')
                fim = datetime.strptime(semana['fim'], '%Y-%m-%d')
                if inicio <= proxima_data <= fim:
                    semana['manutencoes'].append({
                        'maquina': plano.maquina.codigo,
                        'plano': plano.nome
                    })
                    break  # Para de procurar assim que encontrar a semana correta
            proxima_data += timedelta(days=plano.periodicidade)  # Próxima execução

    return JsonResponse(semanas, safe=False)

def ultimas_preventivas(request):
    """
    Retorna as últimas 5 manutenções preventivas planejadas e finalizadas.
    """
    area = request.GET.get('area')

    # Filtra as solicitações planejadas e finalizadas
    solicitacoes = Solicitacao.objects.filter(planejada=True, area=area, status_andamento='finalizada').exclude(maquina__codigo='ETE')

    # Subquery para encontrar a última execução de cada solicitação
    ultima_execucao_subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao')

    # Anota o número e a última atualização da execução
    data = solicitacoes.annotate(
        ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1]),
        ultima_atualizacao=Subquery(ultima_execucao_subquery.values('ultima_atualizacao')[:1])
    ).values(
        'id', 'ultima_execucao_n', 'ultima_atualizacao', 'maquina__codigo', 'descricao'
    ).order_by('-ultima_atualizacao')[:5]

    # Retorna a resposta JSON com os dados serializáveis
    return JsonResponse({'data': list(data)})

def preventivas_em_aberto(request):
    """
    Retorna uma lista de preventivas em aberto, mostrando apenas o maior n_execucao
    (última execução) para cada ordem em aberto, limitado ao top 5.
    """

    area = request.GET.get('area')

    # Filtra as solicitações planejadas e abertas
    solicitacoes = Solicitacao.objects.filter(
        planejada=True,
        area=area
    ).filter(
        ~Q(maquina__codigo='ETE'),  # Máquina diferente de 'ETE'
        ~Q(status_andamento='finalizada')  # Status diferente de 'finalizada'
    )

    # Subquery para encontrar a maior execução para cada ordem
    ultima_execucao_subquery = Execucao.objects.filter(
        ordem=OuterRef('pk')
    ).order_by('-n_execucao')

    # Anota o número da maior execução e a última atualização para cada ordem
    solicitacoes_anotadas = solicitacoes.annotate(
        ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1]),
        ultima_atualizacao=Subquery(ultima_execucao_subquery.values('ultima_atualizacao')[:1])
    ).order_by('-ultima_execucao_n')  # Ordena pelas maiores execuções

    # Limita o resultado ao top 5
    top_5_solicitacoes = solicitacoes_anotadas[:5]

    # Serializa os dados para JSON
    data = top_5_solicitacoes.values(
        'id', 'maquina__codigo', 'descricao', 'ultima_execucao_n', 'ultima_atualizacao'
    )

    return JsonResponse({'data': list(data)})

def excluir_plano_preventiva(request, pk):
    plano = get_object_or_404(PlanoPreventiva, pk=pk)

    # Atualiza o campo 'status' para False
    plano.ativo = False
    plano.save()
    
    return JsonResponse({'success': 'success'})

def calcular_proximas_preventivas(plano):
    """
    Calcula as próximas preventivas com base na última execução e na periodicidade do plano.
    Retorna apenas datas dentro do ano atual.
    """
    # Obtém a última execução do plano
    ultima_solicitacao = SolicitacaoPreventiva.objects.filter(
        plano=plano, finalizada=True
    ).order_by('-data').first()

    # Se não houver última execução, usa a data_base do plano
    data_base = ultima_solicitacao.data if ultima_solicitacao else plano.data_base

    if not data_base:
        # Se nenhuma data_base ou última execução estiver definida, não há como calcular
        return []

    # Lista para armazenar as próximas preventivas
    proximas_preventivas = []

    # Calcula as próximas preventivas dentro do ano atual
    data_atual = date.today()
    ano_atual = data_atual.year

    # Começa a partir da data base
    proxima_data = data_base + timedelta(days=plano.periodicidade)

    while proxima_data.year == ano_atual:
        proximas_preventivas.append(proxima_data.strftime('%d/%m/%Y'))
        proxima_data += timedelta(days=plano.periodicidade)

    return proximas_preventivas


def buscar_historico(request):
    item_id = request.GET.get('id')  # ID da máquina ou do item

    if not item_id:
        return JsonResponse({'error': 'ID não fornecido'}, status=400)

    try:
        # Obter o plano preventivo específico
        plano = PlanoPreventiva.objects.get(pk=item_id)

        # Calcula as próximas preventivas
        proximas_preventivas = calcular_proximas_preventivas(plano)

        # Filtra as solicitações planejadas para a máquina do plano, excluindo 'ETE'
        solicitacoes = Solicitacao.objects.filter(
            planejada=True,
            maquina__codigo=plano.maquina.codigo,
            status='aprovar'
        ).exclude(
            maquina__codigo='ETE'
        )

        # Subquery para encontrar a última execução de cada solicitação
        ultima_execucao_subquery = Execucao.objects.filter(
            ordem=OuterRef('pk')
        ).order_by('-n_execucao')

        # Anota o número da última execução e sua última atualização
        solicitacoes_anotadas = solicitacoes.annotate(
            ultima_execucao_n=Subquery(ultima_execucao_subquery.values('n_execucao')[:1]),
            ultima_atualizacao=Subquery(ultima_execucao_subquery.values('ultima_atualizacao')[:1]),
            data_fim=Subquery(ultima_execucao_subquery.values('data_fim')[:1])    
        ).values(
            'id', 'ultima_execucao_n', 'ultima_atualizacao','data_fim', 'maquina__codigo', 'descricao', 'status_andamento'
        ).order_by('-data_fim')

        # Prepara os dados do histórico das preventivas realizadas
        historico_preventivas = []
        for solicitacao in solicitacoes_anotadas:
            historico_preventivas.append({
                "os": solicitacao['id'],
                "data": solicitacao['data_fim'],
                "descricao": solicitacao['descricao'],
                "status": solicitacao['status_andamento'] if solicitacao['status_andamento'] else "Sem execução"
            })

        # Retornar os dados como JSON
        return JsonResponse({
            "proximas_preventivas": proximas_preventivas,
            "historico_preventivas": historico_preventivas,
        })

    except PlanoPreventiva.DoesNotExist:
        return JsonResponse({'error': 'Item não encontrado'}, status=404)

