from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Value, CharField, ExpressionWrapper, fields
from django.db.models.functions import Concat
from django.contrib.postgres.aggregates import StringAgg

from solicitacao.models import Solicitacao
from execucao.models import Execucao, InfoSolicitacao, MaquinaParada
from cadastro.models import Maquina, Setor, Operador
from preventiva.models import SolicitacaoPreventiva, PlanoPreventiva

from wpp.utils import OrdemServiceWpp
from home.utils import buscar_telefone

from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

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
            motivo_atraso = request.POST.get("motivo_atraso")

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

            if solicitacao.maq_parada == False:
                if apos_exec_maq_parada:
                    solicitacao.maq_parada = True
                
            solicitacao.status_andamento = status

            if motivo_atraso:
                solicitacao.motivo_atraso = motivo_atraso

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
                        'maquina': solicitacao.maquina.codigo if solicitacao.maquina else solicitacao.tipo_ferramenta,
                        'motivo': solicitacao.descricao,
                        'descricao': solicitacao.maquina.descricao if solicitacao.maquina else solicitacao.codigo_ferramenta,
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
            print(request.POST.get('id_maquina'))
            print(request.POST.get('id_setor'))
            maquina = request.POST.get('id_maquina')
            setor = request.POST.get('id_setor')
            comentario_pcm = request.POST.get('comentario_manutencao')
            data_abertura = parse_datetime(request.POST.get('data_abertura'))
            if not data_abertura:
                raise ValueError('Data de abertura inválida.')
            
            setor_maq_solda = request.POST.get('setor_maq_solda', None)
            equipamento_em_falha = request.POST.get('eq_falha', None)
            tipo_ferramenta = request.POST.get('tipo_ferramenta', None)
            codigo_ferramenta = request.POST.get('codigo_ferramenta', None)

            print(setor_maq_solda)
            print(equipamento_em_falha)
            print(tipo_ferramenta)
            print(codigo_ferramenta)

            print(request.POST)

            programacao = parse_datetime(request.POST.get('data_programacao'))
            programacao = programacao if programacao else None

            data_inicio = data_abertura
            data_fim = data_abertura
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

                    # Campos exclusivos para o setor de Solda
                    # Ao editar a primeira execução
                    solicitacao.setor_maq_solda = setor_maq_solda
                    solicitacao.equipamento_em_falha = equipamento_em_falha
                    solicitacao.tipo_ferramenta = tipo_ferramenta
                    solicitacao.codigo_ferramenta = codigo_ferramenta

                    solicitacao.maq_parada = True if request.POST.get('flagMaqParada') == 'on' else False

                    if tipo_manutencao == 'preventiva_programada':
                        solicitacao.planejada = True

                solicitacao.comentario_manutencao = comentario_pcm
                solicitacao.data_abertura = data_abertura
                solicitacao.status = status_inicial
                solicitacao.status_andamento = 'em_espera'

                if maquina:
                    solicitacao.maquina = get_object_or_404(Maquina, pk=maquina)
                elif tipo_ferramenta is not None:
                    solicitacao.maquina = None

                if setor:
                    solicitacao.setor = get_object_or_404(Setor, pk=setor)

                solicitacao.save()

                if status_inicial == 'rejeitar' and solicitacao.area == 'predial' and solicitacao.solicitante.is_active:

                    telefone = buscar_telefone(solicitacao.solicitante.matricula)

                    if telefone:
                        if solicitacao.maquina:
                            local_maquina = f"{solicitacao.maquina.codigo} - {solicitacao.maquina.descricao}"
                        elif solicitacao.tarefa:
                            local_maquina = str(solicitacao.tarefa)
                        elif solicitacao.codigo_ferramenta:
                            local_maquina = solicitacao.codigo_ferramenta
                        else:
                            local_maquina = solicitacao.setor.nome

                        kwargs = {
                            'ordem': solicitacao.pk,
                            'data_abertura': solicitacao.data_abertura,
                            'local_maquina': local_maquina,
                            'motivo': solicitacao.descricao or 'Nao informado',
                            'motivo_cancelamento': comentario_pcm or 'Nao informado',
                            'solicitante': solicitacao.solicitante.nome
                        }

                        try:
                            ordem_service = OrdemServiceWpp()
                            ordem_service.mensagem_ordem_rejeitada_predial(telefone, kwargs)
                        except:
                            pass

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

        if ultima_execucao:
            if data_inicio < ultima_execucao.data_fim:
                return JsonResponse({
                    'error': 'A data de início deve ser posterior à data final da última execução.'
                }, status=400)
            if data_fim < data_inicio:
                return JsonResponse({
                    'error': 'A data de fim deve ser posterior à data de início.'
                }, status=400)

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
        'n_execucao',
        'ordem__setor__nome',
        'ordem__solicitante__nome',
        'ordem__maquina__codigo',
        'ordem__comentario_manutencao',
        'ordem__descricao',
        'operadores',
        'ordem__area',
        'ordem__data_abertura',
        'data_inicio',
        'data_fim',
        'observacao',
        'status',
        'ordem__info_solicitacao__tipo_manutencao',
        'ordem__info_solicitacao__area_manutencao',
        'ultima_atualizacao',
        'horas_executada',
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
    )

    # Verifica se é exportação ou não
    filtros_estado = {}
    print(request.POST)
    exportar_plan = request.POST.get('exportar_xlsx', '')

    # Filtros personalizados
    # Grupo 1: Identificação da Ordem 
    ordem = request.POST.get('ordem', '')
    execucao = request.POST.get('execucao', '')
    setor = request.POST.get('setor', '')
    solicitante = request.POST.get('solicitante', '')
    operador = request.POST.getlist('operador[]', '')
    area = request.POST.get('area', '')

    # // Grupo 2: Máquina e Manutenção
    maquina = request.POST.get('maquina', '')
    tipo_manutencao = request.POST.getlist('tipoManutencao[]')
    area_manutencao = request.POST.getlist('areaManutencao[]', '')
    horas_executadas_inicial = request.POST.get('horasExecutadasInicial', '')
    horas_executadas_final = request.POST.get('horasExecutadasFinal', '')

    # Grupo 3: Datas
    data_abertura_inicial = request.POST.get('dataAberturaInicial', '')
    data_abertura_final = request.POST.get('dataAberturaFinal', '')
    data_inicio_inicial = request.POST.get('dataInicioInicial', '')
    data_inicio_final = request.POST.get('dataInicioFinal', '')
    data_final_inicial = request.POST.get('dataFinalInicial', '')
    data_final_final = request.POST.get('dataFinalFinal', '')
    ultima_atualizacao_inicial = request.POST.get('ultimaAtualizacaoInicial', '')
    ultima_atualizacao_final = request.POST.get('ultimaAtualizacaoFinal', '')
    
    # Grupo 4: Comentários e Status
    comentario_manutencao = request.POST.get('comentarioManutencao', '')
    motivo = request.POST.get('motivo', '')
    obs_executante = request.POST.get('obsExecutante', '')
    status = request.POST.getlist('status[]', '')

    # Verificação de intervalo de horas correto
    horas_executadas_corretas = True
    if len(horas_executadas_inicial) > 0 and len(horas_executadas_final) > 0:
        try:
            hora_ini = str_para_timedelta(horas_executadas_inicial)
            hora_fim = str_para_timedelta(horas_executadas_final)
            
            if hora_ini > hora_fim:
                horas_executadas_corretas = False
        except ValueError:
            horas_executadas_corretas = False  # formato inválido
    

    # Validação intervalo data abertura
    data_abertura_intervalo_correto = True
    if len(data_abertura_inicial) > 0 and len(data_abertura_final) > 0:
        data_abertura_inicial_datetime = datetime.strptime(data_abertura_inicial, "%Y-%m-%d")
        data_abertura_final_datetime = datetime.strptime(data_abertura_final, "%Y-%m-%d")
        if data_abertura_inicial_datetime > data_abertura_final_datetime:
            data_abertura_intervalo_correto = False
    
    # Validação intervalo data inicio
    data_inicio_intervalo_correto = True
    if len(data_inicio_inicial) > 0 and len(data_inicio_final) > 0:
        data_inicio_inicial_datetime = datetime.strptime(data_inicio_inicial, "%Y-%m-%d")
        data_inicio_final_datetime = datetime.strptime(data_inicio_final, "%Y-%m-%d")
        if data_inicio_inicial_datetime > data_inicio_final_datetime:
            data_inicio_intervalo_correto = False

    # Validação intervalo data final
    data_final_intervalo_correto = True
    if len(data_final_inicial) > 0 and len(data_final_final) > 0:
        data_final_inicial_datetime = datetime.strptime(data_final_inicial, "%Y-%m-%d")
        data_final_final_datetime = datetime.strptime(data_final_final, "%Y-%m-%d")
        if data_final_inicial_datetime > data_final_final_datetime:
            data_final_intervalo_correto = False

    # Validação intervalo data final
    ultima_atualizacao_intervalo_correto = True
    if len(ultima_atualizacao_inicial) > 0 and len(ultima_atualizacao_final) > 0:
        ultima_atualizacao_inicial_datetime = datetime.strptime(ultima_atualizacao_inicial, "%Y-%m-%d")
        ultima_atualizacao_final_datetime = datetime.strptime(ultima_atualizacao_final, "%Y-%m-%d")
        if ultima_atualizacao_inicial_datetime > ultima_atualizacao_final_datetime:
            ultima_atualizacao_intervalo_correto = False

    if ordem:
        execucoes = execucoes.filter(ordem__pk=ordem)
    if execucao:
        execucoes = execucoes.filter(n_execucao=execucao)
    if setor:
        execucoes = execucoes.filter(ordem__setor=setor)
    if solicitante:
        execucoes = execucoes.filter(solicitante__icontains=solicitante)
    if operador:
        execucoes = execucoes.filter(operador__id__in=operador)
    if area:
        execucoes = execucoes.filter(ordem__area__icontains=area)
    if status:
        execucoes = execucoes.filter(status__in=status)
    if maquina:
        execucoes = execucoes.filter(ordem__maquina=maquina)
    if tipo_manutencao:
        execucoes = execucoes.filter(ordem__info_solicitacao__tipo_manutencao__in=tipo_manutencao)
    if area_manutencao:
        execucoes = execucoes.filter(ordem__info_solicitacao__area_manutencao__in=area_manutencao)
    if horas_executadas_inicial:
        if horas_executadas_corretas:
            delta_hora_inicial = str_para_timedelta(horas_executadas_inicial)
            execucoes = execucoes.filter(horas_executada__gte=delta_hora_inicial)
    if horas_executadas_final:
        if horas_executadas_corretas:
            delta_hora_final = str_para_timedelta(horas_executadas_final)
            print('testes ',delta_hora_final)
            execucoes = execucoes.filter(horas_executada__lte=delta_hora_final)

    if data_abertura_inicial:
        if data_abertura_intervalo_correto:
            execucoes = execucoes.filter(ordem__data_abertura__date__gte=datetime.strptime(data_abertura_inicial, "%Y-%m-%d").date())
    if data_abertura_final:
        if data_abertura_intervalo_correto:
            execucoes = execucoes.filter(ordem__data_abertura__date__lte=datetime.strptime(data_abertura_final, "%Y-%m-%d").date())
    if data_inicio_inicial:
        if data_inicio_intervalo_correto:
            execucoes = execucoes.filter(data_inicio__date__gte=datetime.strptime(data_inicio_inicial, "%Y-%m-%d").date())
    if data_inicio_final:
        if data_inicio_intervalo_correto:
            execucoes = execucoes.filter(data_inicio__date__lte=datetime.strptime(data_inicio_final, "%Y-%m-%d").date())
    if data_final_inicial:
        if data_final_intervalo_correto:
            execucoes = execucoes.filter(data_fim__date__gte=datetime.strptime(data_final_inicial, "%Y-%m-%d").date())
    if data_final_final:
        if data_final_intervalo_correto:
            execucoes = execucoes.filter(data_fim__date__lte=datetime.strptime(data_final_final, "%Y-%m-%d").date())
    if ultima_atualizacao_inicial:
        if ultima_atualizacao_intervalo_correto:
            execucoes = execucoes.filter(ultima_atualizacao__date__gte=datetime.strptime(ultima_atualizacao_inicial, "%Y-%m-%d").date())
    if ultima_atualizacao_final:
        if ultima_atualizacao_intervalo_correto:
            execucoes = execucoes.filter(ultima_atualizacao__date__lte=datetime.strptime(ultima_atualizacao_final, "%Y-%m-%d").date())

    if comentario_manutencao:
        execucoes = execucoes.filter(ordem__comentario_manutencao__icontains=comentario_manutencao)
    if motivo:
        execucoes = execucoes.filter(ordem__descricao__icontains=motivo)
    if obs_executante:
        execucoes = execucoes.filter(ordem__observacao__icontains=obs_executante)

    # Aplicando ordenação
    if order_column != 'operadores':
        execucoes = execucoes.order_by(order_column)

    if exportar_plan:
        for key, value in request.POST.items():
            # Pega apenas as chaves que começam com 'filtrosEstado['
            if key.startswith('filtrosEstado[') and key.endswith(']'):
                # Extrai o nome dentro dos colchetes
                nome_campo = key[len('filtrosEstado['):-1]
                filtros_estado[nome_campo] = value

        # Agora filtros_estado é um dict com todos os parâmetros
        # Ex: {'OS': 'true', 'Execução': 'true', ...}
        print(filtros_estado)

        return exportar_excel(execucoes, filtros_estado)

    # Paginação
    paginator = Paginator(execucoes, length)
    execucoes_page = paginator.get_page(start // length + 1)

    data = []
    for execucao in execucoes_page:
        data.append({
            'ordem': f"#{execucao.ordem.pk}",
            'execucao': execucao.n_execucao,
            'setor': str(execucao.ordem.setor.nome),
            'solicitante': execucao.solicitante,
            'maquina': execucao.maquina,
            'comentario_manutencao': execucao.ordem.comentario_manutencao,
            'motivo': execucao.ordem.descricao,
            'operadores': ', '.join(execucao.operador.values_list('nome', flat=True)),
            'area': execucao.ordem.area,
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

def exportar_excel(queryset, filtros_estado):
    """
    Gera e retorna um arquivo Excel a partir de um queryset ou lista de dicionários.
    """
    # Mapeia cada campo visível para o nome de coluna no banco
    FIELD_MAP = {
        'OS': 'ordem__pk',
        'Execução': 'n_execucao',
        'Setor': 'ordem__setor__nome',
        'Solicitante': 'solicitante',
        'Máquina': 'maquina',
        'Comentário da manutenção': 'ordem__comentario_manutencao',
        'Motivo': 'ordem__descricao',
        'Operadores': 'operadores',  # virá via annotate
        'Área': 'ordem__area',
        'Data de abertura': 'ordem__data_abertura',
        'Data de início': 'data_inicio',
        'Data de fim': 'data_fim',
        'Obs do executante': 'observacao',
        'Status': 'status',
        'Tipo da manutenção': 'tipo_manutencao',
        'Área da manutenção': 'area_manutencao',
        'Última atualização': 'ultima_atualizacao',
        'Horas executadas': 'horas_executada',
    }

    # Campos ativos
    campos_ativos = [
        campo for campo, ativo in filtros_estado.items()
        if ativo == 'true' and campo in FIELD_MAP
    ]

    if not campos_ativos:
        return HttpResponse("Nenhum campo selecionado.", status=400)
    
    queryset = (
        queryset
        .select_related('ordem__setor', 'ordem__maquina')
        .annotate(operadores=StringAgg('operador__nome', delimiter=', '))
        .values(*[FIELD_MAP[c] for c in campos_ativos])
    )
        
    # Cria DataFrame com pandas
    df = pd.DataFrame(list(queryset))

    df.rename(columns={FIELD_MAP[c]: c for c in campos_ativos}, inplace=True)

    # Formata datas (apenas se estiverem presentes)
    for col in ['Data de abertura', 'Data de início', 'Data de fim', 'Última atualização']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime("%d/%m/%Y %H:%M")

    # Salva em memória (sem gravar arquivo)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Histórico Execuções')

    # Move o ponteiro para o início
    output.seek(0)

    # Cria a resposta HTTP com o conteúdo do arquivo
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # Define o nome do arquivo que será baixado
    response['Content-Disposition'] = 'attachment; filename="execucoes.xlsx"'

    return response

def str_para_timedelta(horas_str):
    h, m = map(int, horas_str.split(":"))
    print(h, m)
    return timedelta(hours=h, minutes=m)
