from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.template.loader import render_to_string

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao
from cadastro.models import Maquina, Setor
from wpp.utils import OrdemServiceWpp
from home.utils import buscar_telefone

import datetime

ordem_service = OrdemServiceWpp()

@login_required
@csrf_exempt
def criar_execucao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

    ultima_execucao = Execucao.objects.filter(ordem=solicitacao).order_by('n_execucao').last()
    n_execucao = ultima_execucao.n_execucao + 1 if ultima_execucao else 0

    if request.method == 'POST':

        if n_execucao == 1:

            tipo_manutencao = request.POST.get('tipo_manutencao')
            area_manutencao = request.POST.get('area_manutencao')

            infoSolicitacao = InfoSolicitacao.objects.create(
                solicitacao=solicitacao,
                tipo_manutencao=tipo_manutencao,
                area_manutencao=area_manutencao,
            )

            infoSolicitacao.save()

        data_inicio = parse_datetime(request.POST.get('data_inicio'))
        data_fim = parse_datetime(request.POST.get('data_fim'))
        observacao = request.POST.get('observacao')
        operadores = request.POST.getlist('operador')
        status = request.POST.get('status')
        che_maq_parada = request.POST.get('che_maq_parada') == 'on'
        exec_maq_parada = request.POST.get('exec_maq_parada') == 'on'
        apos_exec_maq_parada = request.POST.get('apos_exec_maq_parada') == 'on'

        if not apos_exec_maq_parada:
            solicitacao.maq_parada = False
            
        solicitacao.status_andamento = status

        solicitacao.save()

        execucao = Execucao.objects.create(
            ordem=solicitacao,
            n_execucao=n_execucao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            observacao=observacao,
            status=status,
            che_maq_parada=che_maq_parada,
            exec_maq_parada=exec_maq_parada,
            apos_exec_maq_parada=apos_exec_maq_parada,
        )

        execucao.operador.set(operadores)
        execucao.save()

        if status == 'finalizada':
            # Obtendo o telefone do solicitante
            telefone = buscar_telefone(solicitacao.solicitante.matricula)

            link_satisfacao = request.build_absolute_uri(reverse('pagina_satisfacao', args=[solicitacao.pk]))

            if telefone:  # Verifica se o telefone foi encontrado
                kwargs = {
                    'ordem': solicitacao.pk,
                    'data_abertura': solicitacao.data_abertura,
                    'data_fechamento': execucao.data_fim,
                    'maquina': solicitacao.maquina.codigo,
                    'motivo': solicitacao.descricao,
                    'descricao': solicitacao.maquina.descricao,
                    'link': link_satisfacao
                }

                # Cria uma instância de OrdemServiceWpp
                ordem_service = OrdemServiceWpp()

                # Chamando o método mensagem_finalizar_ordem
                status_code, response_data = ordem_service.mensagem_finalizar_ordem(telefone, kwargs)

                # criar uma pagina para o usuario confirmar a finalização da ordem, deverá ser dois botões de sim ou não.


            else:
                print("Telefone não encontrado para o solicitante.")
            
        # Sempre retorna ou redireciona após o processamento
        return redirect('home_producao')

@csrf_exempt
def editar_solicitacao(request, solicitacao_id):

    solicitacao = get_object_or_404(Solicitacao, id=solicitacao_id)

    if request.method == 'POST':

        comentario_pcm = request.POST.get('comentario_manutencao')
        data_abertura = parse_datetime(request.POST.get('data_abertura'))

        data_inicio = datetime.datetime.now()
        data_fim = datetime.datetime.now()
        status = 'em_espera'
        status_inicial = request.POST.get('status_inicial')

        # Criar uma nova execução
        execucao = Execucao.objects.create(
            ordem=solicitacao,
            n_execucao=0,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status,
            che_maq_parada=True if request.POST.get('flagMaqParada') else False,
            exec_maq_parada=True if request.POST.get('flagMaqParada') else False,
            apos_exec_maq_parada=True if request.POST.get('flagMaqParada') else False,
        )

        # Atualizar a solicitação
        solicitacao.comentario_manutencao = comentario_pcm
        solicitacao.data_abertura = data_abertura
        solicitacao.status = status_inicial
        solicitacao.status_andamento = status

        if request.POST.get('flagMaqParada'):
            solicitacao.maq_parada = True

        solicitacao.save()

        # Retorna uma resposta de sucesso em JSON
        return JsonResponse({
            'success': True,
        })

    return redirect('home_producao')

@login_required
@csrf_exempt
def criar_execucao_predial(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

    ultima_execucao = Execucao.objects.filter(ordem=solicitacao).order_by('n_execucao').last()
    n_execucao = ultima_execucao.n_execucao + 1 if ultima_execucao else 1

    if request.method == 'POST':
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        observacao = request.POST.get('observacao')
        operadores = request.POST.getlist('operador')
        status = request.POST.get('status')
        tipo_manutencao = request.POST.get('tipo_manutencao')
        area_manutencao = 'predial'

        if n_execucao == 1:

            infoSolicitacao = InfoSolicitacao.objects.create(
                solicitacao=solicitacao,
                tipo_manutencao=tipo_manutencao,
                area_manutencao=area_manutencao,
            )

            infoSolicitacao.save()

        execucao = Execucao.objects.create(
            ordem=solicitacao,
            n_execucao=n_execucao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            observacao=observacao,
            status=status,
        )

        execucao.operador.set(operadores)
        # execucao.save()

        return redirect('home_predial')

    return redirect('home_predial')

@login_required
def historico_execucao(request):
    return render(request, 'execucao/historico.html')

@csrf_exempt
def execucao_data(request):
    draw = int(request.POST.get('draw', 0))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))

    # Ordenação
    order_column_index = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'asc')
    
    columns = [
        'ordem__pk', 
        'data_inicio',
        'data_fim',
        'ordem__solicitante__nome', 
        'observacao',
        'ultima_atualizacao',
        'ordem__setor__nome', 
        'ordem__maquina__codigo',
        'status',
        'ordem__area'
    ]
            
    order_column = columns[order_column_index]

    if order_dir == 'desc':
        order_column = '-' + order_column

    # Filtrando as execuções (se houver busca)
    search_value = request.POST.get('search[value]', '')

    if request.user.is_staff:
        execucoes = Execucao.objects.all()
    else:
        execucoes = Execucao.objects.filter(ordem__area=request.user.area)

    if search_value:
        execucoes = execucoes.filter(
            ordem__pk__icontains=search_value
        )

    # Aplicando ordenação
    execucoes = execucoes.order_by(order_column)

    # Paginação
    paginator = Paginator(execucoes, length)
    execucoes_page = paginator.get_page(start // length + 1)

    data = []
    for execucao in execucoes_page:
        data.append({
            'ordem': f"#{execucao.ordem.pk}",
            'data_inicio': execucao.data_inicio.strftime("%d/%m/%Y %H:%M"),
            'data_fim': execucao.data_fim.strftime("%d/%m/%Y %H:%M") if execucao.data_fim else '',
            'solicitante': str(execucao.ordem.solicitante),
            'che_maq_parada': execucao.che_maq_parada,
            'exec_maq_parada': execucao.exec_maq_parada,
            'apos_exec_maq_parada': execucao.apos_exec_maq_parada,
            'observacao': execucao.observacao,
            'ultima_atualizacao': execucao.ultima_atualizacao.strftime("%d/%m/%Y %H:%M"),
            'setor': str(execucao.ordem.setor),
            'maquina': f"{execucao.ordem.maquina.codigo} - {execucao.ordem.maquina.descricao}",
            'status': execucao.status,
            'area': execucao.ordem.area
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': paginator.count,
        'recordsFiltered': paginator.count,
        'data': data,
    })

