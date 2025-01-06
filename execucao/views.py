from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Value, CharField, ExpressionWrapper, fields
from django.db.models.functions import Concat

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao, MaquinaParada
from cadastro.models import Maquina, Setor, Operador
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
            che_maq_parada = request.POST.get('che_maq_parada') == 'sim'
            exec_maq_parada = request.POST.get('exec_maq_parada') == 'sim'
            apos_exec_maq_parada = request.POST.get('apos_exec_maq_parada') == 'sim'
            
            # Campos apenas para ETE
            pvlye = float(request.POST.get('pvlye').replace(",",".")) if request.POST.get('pvlye') else None
            paplus = float(request.POST.get('paplus').replace(",",".")) if request.POST.get('paplus') else None
            tratamento_ete = request.POST.get('tratamento_ete', None)
            phagua = float(request.POST.get('phagua').replace(",",".")) if request.POST.get('phagua') else None

            if ultima_execucao:
                if data_inicio < ultima_execucao.data_fim:
                    return JsonResponse({
                        'error': 'A data de início deve ser posterior à data final da última execução.'
                    }, status=400)
                if data_fim < data_inicio:
                    return JsonResponse({
                        'error': 'A data de fim deve ser posterior à data de início.'
                    }, status=400)

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
                paplus=paplus,
                ph_agua=phagua,
                pvlye=pvlye,
                tratamento_ete=tratamento_ete,

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

                    try:
                        ordem_service = OrdemServiceWpp()
                        status_code, response_data = ordem_service.mensagem_finalizar_ordem(telefone, kwargs)
                    except:
                        pass

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
            maquina = request.POST.get('id_maquina')
            setor = request.POST.get('id_setor')
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
            if not tipo_manutencao:
                tipo_manutencao = request.POST.get('tipo_manutencao_display')
                
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
                    execucao = Execucao.objects.create(
                        ordem=solicitacao,
                        # n_execucao=0,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        status='em_espera',
                        che_maq_parada=request.POST.get('che_maq_parada') == 'sim',
                        exec_maq_parada=request.POST.get('exec_maq_parada') == 'sim',
                        apos_exec_maq_parada=True if request.POST.get('flagMaqParada') == 'on' else False
                    )

                    execucao.save()

                    solicitacao.programacao = programacao
                    solicitacao.atribuido = responsavel_object
                    solicitacao.prioridade = nivel_prioridade

                    if request.POST.get('flagMaqParada') == 'on':
                        solicitacao.maq_parada = True

                    if tipo_manutencao == 'preventiva_programada':
                        solicitacao.planejada = True

                solicitacao.comentario_manutencao = comentario_pcm
                solicitacao.data_abertura = data_abertura
                solicitacao.status = status_inicial
                solicitacao.status_andamento = 'em_espera'

                if maquina:
                    solicitacao.maquina = get_object_or_404(Maquina, pk=maquina)
                if setor:
                    solicitacao.setor = get_object_or_404(Setor, pk=setor)

                solicitacao.save()

                if not status_inicial == 'rejeitar':
                    if tipo_manutencao == 'preventiva_programada' and plano:
                        SolicitacaoPreventiva.objects.create(
                            ordem=solicitacao,
                            plano=get_object_or_404(PlanoPreventiva, id=plano),
                            data=timezone.now().date()
                        )
                    try:
                        if responsavel_object and hasattr(responsavel_object, 'telefone'):
                            telefone = responsavel_object.telefone
                            kwargs = {
                                'ordem': solicitacao.pk,
                                'solicitante': solicitacao.solicitante,
                                'maquina': solicitacao.maquina.descricao,
                                'motivo': solicitacao.descricao,
                                'prioridade': solicitacao.get_prioridade_display()  # Usando o display
                            }
                            
                            ordem_service = OrdemServiceWpp()
                            status_code, response_data = ordem_service.mensagem_atribuir_ordem(telefone, kwargs)
                    except:
                        pass

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

    setores = Setor.objects.all()

    return render(request, 'execucao/historico.html', {'setores':setores})

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
        'n_execucao',
        'ordem__setor__nome',
        'ordem__solicitante__nome',
        'ordem__maquina__codigo',
        'ordem__comentario_manutencao',
        'ordem__descricao',
        'ordem__data_abertura',
        'data_inicio',
        'data_fim',
        'observacao',
        'status',
        'ordem__info_solicitacao__tipo_manutencao',
        'ordem__info_solicitacao__area_manutencao',
        'ultima_atualizacao',
        'horas_executada'      
    ] 

    order_column = columns[order_column_index]

    if order_dir == 'desc':
        order_column = '-' + order_column

    # Filtrando execuções
    # search_value = request.POST.get('search[value]', '')

    execucoes = Execucao.objects.annotate(
        solicitante=Concat(
            F('ordem__solicitante__matricula'),
            Value(' - '),
            F('ordem__solicitante__nome'),
            output_field=CharField()
        ),
        maquina=Concat(
            F('ordem__maquina__codigo'),
            Value(' - '),
            F('ordem__maquina__descricao'),
            output_field=CharField()
        ),
        horas_executada=ExpressionWrapper(
            F('data_fim') - F('data_inicio'),
            output_field=fields.DurationField()
        ),
        tipo_manutencao=F('ordem__info_solicitacao__tipo_manutencao'),  # Atualize o nome aqui
        area_manutencao=F('ordem__info_solicitacao__area_manutencao')  # Atualize o nome aqui
    ).filter(
        ordem__status="aprovar",
        ordem__area="producao"
    )

    # if search_value:
    #     execucoes = execucoes.filter(ordem__pk__icontains=search_value)

    # Filtros personalizados
    status = request.POST.get('status', '')
    setor = request.POST.get('area', '')
    print(setor)
    solicitante = request.POST.get('solicitante', '')
    data_inicio = request.POST.get('data_inicio', '')

    if status:
        execucoes = execucoes.filter(status=status)
    if setor:
        execucoes = execucoes.filter(ordem__setor__nome=setor)
    if solicitante:
        execucoes = execucoes.filter(solicitante__icontains=solicitante)
    if data_inicio:
        execucoes = execucoes.filter(data_inicio__date=data_inicio)

    # Aplicando ordenação
    execucoes = execucoes.order_by(order_column)

    # Paginação
    paginator = Paginator(execucoes, length)
    execucoes_page = paginator.get_page(start // length + 1)

    data = []
    for execucao in execucoes_page:
        data.append({
            'ordem': f"#{execucao.ordem.pk}",
            'execucao': execucao.id,
            'setor': str(execucao.ordem.setor.nome),
            'solicitante': execucao.solicitante,
            'maquina': execucao.maquina,
            'comentario_manutencao': execucao.ordem.comentario_manutencao,
            'motivo': execucao.ordem.descricao,
            'data_abertura': execucao.ordem.data_abertura.strftime("%d/%m/%Y %H:%M"),
            'data_inicio': execucao.data_inicio.strftime("%d/%m/%Y %H:%M"),
            'data_fim': execucao.data_fim.strftime("%d/%m/%Y %H:%M") if execucao.data_fim else '',
            'observacao': execucao.observacao,
            'status': execucao.status,
            'tipo_manutencao': execucao.tipo_manutencao,
            'area_manutencao': execucao.area_manutencao,
            'ultima_atualizacao': execucao.ultima_atualizacao.strftime("%d/%m/%Y %H:%M"),
            'horas_executada': str(execucao.horas_executada),
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': paginator.count,
        'recordsFiltered': paginator.count,
        'data': data,
    })
