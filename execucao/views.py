from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao
from cadastro.models import Maquina, Setor, Operador
from funcionario.models import Funcionario
from preventiva.models import SolicitacaoPreventiva, PlanoPreventiva

from wpp.utils import OrdemServiceWpp
from home.utils import buscar_telefone

import datetime

ordem_service = OrdemServiceWpp()
User = get_user_model()

@login_required
@csrf_exempt
def criar_execucao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

    ultima_execucao = Execucao.objects.filter(ordem=solicitacao).order_by('n_execucao').last()
    n_execucao = ultima_execucao.n_execucao + 1 if ultima_execucao else 0

    if request.method == 'POST':
        
        with transaction.atomic():
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

                # Se o operador quiser reabrir uma nova ordem com um novo motivo
                if request.POST.get('motivoNovaOrdemInput'):
                
                    Solicitacao.objects.create(
                        setor=solicitacao.setor,
                        maquina=solicitacao.maquina,
                        maq_parada=False,
                        solicitante=request.user,
                        equipamento_em_falha=solicitacao.equipamento_em_falha,
                        setor_maq_solda=solicitacao.setor_maq_solda,
                        impacto_producao=solicitacao.impacto_producao,
                        tipo_ferramenta=solicitacao.tipo_ferramenta,
                        codigo_ferramenta=solicitacao.codigo_ferramenta,
                        video=solicitacao.video,
                        descricao=request.POST.get('motivoNovaOrdemInput'),
                        area=solicitacao.area,
                        planejada=False,
                        prioridade=solicitacao.prioridade,
                        tarefa=solicitacao.tarefa,
                        comentario_manutencao=solicitacao.comentario_manutencao,
                        status=solicitacao.status,
                        satisfacao_registrada=False
                    )

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

                else:
                    print("Telefone não encontrado para o solicitante.")

            return JsonResponse({
                'success': True,
            })

@csrf_exempt
def editar_solicitacao(request, solicitacao_id):
    solicitacao = get_object_or_404(Solicitacao, id=solicitacao_id)

    if request.method == 'POST':
        try:
            
            # Obtém os dados do formulário
            comentario_pcm = request.POST.get('comentario_manutencao')
            data_abertura = parse_datetime(request.POST.get('data_abertura'))
            if not data_abertura:
                raise ValueError('Data de abertura inválida.')

            programacao = parse_datetime(request.POST.get('data_programacao'))
            programacao = programacao if programacao else None

            data_inicio = timezone.now()
            data_fim = timezone.now()
            status_inicial = request.POST.get('status_inicial')
            nivel_prioridade = request.POST.get('prioridade')
            if not nivel_prioridade:
                nivel_prioridade = None

            tipo_manutencao = request.POST.get('tipo_manutencao')
            area_manutencao = request.POST.get('area_manutencao')
            plano = request.POST.get('escolherPlanoPreventiva')

            responsavel = request.POST.get('operador')

            responsavel_object = None
            if responsavel:
                responsavel_object = get_object_or_404(Operador, id=responsavel)

            with transaction.atomic():
                if status_inicial == 'rejeitar':
                    solicitacao.status_andamento = 'rejeitado'
                else:
                    
                    InfoSolicitacao.objects.update_or_create(
                        solicitacao=solicitacao,
                        defaults={'area_manutencao': area_manutencao, 'tipo_manutencao': tipo_manutencao}
                    )

                    Execucao.objects.create(
                        ordem=solicitacao,
                        n_execucao=0,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        status='em_espera',
                        che_maq_parada=request.POST.get('flagMaqParada') == 'true',
                        exec_maq_parada=request.POST.get('flagMaqParada') == 'true',
                        apos_exec_maq_parada=request.POST.get('flagMaqParada') == 'true',
                    )

                    solicitacao.programacao = programacao
                    solicitacao.atribuido = responsavel_object
                    solicitacao.prioridade = nivel_prioridade

                    if request.POST.get('flagMaqParada') == 'true':
                        solicitacao.maq_parada = True
                    if tipo_manutencao == 'preventiva_programada':
                        solicitacao.planejada = True

                solicitacao.comentario_manutencao = comentario_pcm
                solicitacao.data_abertura = data_abertura
                solicitacao.status = status_inicial
                solicitacao.status_andamento = 'em_espera'
                solicitacao.save()

                if not status_inicial == 'rejeitar':
                    if tipo_manutencao == 'preventiva_programada' and plano:
                        SolicitacaoPreventiva.objects.create(
                            ordem=solicitacao,
                            plano=get_object_or_404(PlanoPreventiva, id=plano),
                            data=timezone.now().date()
                        )

                    if responsavel_object and hasattr(responsavel_object, 'telefone'):
                        telefone = responsavel_object.telefone
                        kwargs = {
                            'ordem': solicitacao.pk,
                            'solicitante': solicitacao.solicitante,
                            'maquina': solicitacao.maquina.descricao,
                            'motivo': solicitacao.descricao,
                            'prioridade': solicitacao.get_prioridade_display()  # Usando o display legível
                        }

                        ordem_service = OrdemServiceWpp()
                        status_code, response_data = ordem_service.mensagem_atribuir_ordem(telefone, kwargs)

                return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

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

