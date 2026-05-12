from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count, Avg


from .forms import MaquinaForm, AddOperadorForm
from .models import Maquina, Operador, Setor, PedidoCompra
from execucao.models import InfoSolicitacao, Execucao
from cadastro.models import TipoTarefas
import psycopg2
from psycopg2 import errors

import json
import pandas as pd

def criar_maquina(request):
    if request.method == 'POST':
        form = MaquinaForm(request.POST, request.FILES)
        try:
            if form.is_valid():
                maquina = form.save(commit=False)  
                maquina.area = request.user.area 
                maquina.save()  
                
                return redirect('list_maquina')
        except IntegrityError as e:
            print("Já existe uma máquina com esse código",e)
            return JsonResponse({
                'erro': 'ERRO! Já existe uma máquina com esse código!'
            },status=400)
        except Exception as e2:
            print("Algo deu errado!",e2) 
            return JsonResponse({
                'erro': 'Algo deu errado! Tente novamente!'
            },status=500)

    elif request.method == 'GET':
        setores = Setor.objects.all()

        return JsonResponse({
            'setores': list(setores.values('id','nome'))
        })
    
    else:
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    

    return HttpResponse(form)
def edit_maquina(request, pk):
    # Obtém a instância de Maquina correspondente ao 'pk' ou retorna 404 se não existir
    maquina = get_object_or_404(Maquina, pk=pk)
    
    if request.method == 'POST':
        # Carrega os dados POST no formulário, junto com os arquivos (foto, por exemplo)
        form = MaquinaForm(request.POST, request.FILES, instance=maquina)
        try:
            if form.is_valid():
                # Salva o formulário e atualiza a instância da Maquina
                form.save()
                # return redirect('list_maquina')  # Redireciona para a lista de máquinas ou para outra página
                return JsonResponse({
                    'status': 'sucesso'
                })
        except IntegrityError as e:
            print("Já existe uma máquina com esse código",e)
            return JsonResponse({
                'erro': 'ERRO! Já existe uma máquina com esse código!'
                },status=400)
        except Exception as e2:
            print("Algo deu errado!",e2) 
            return JsonResponse({
                'erro': 'Algo deu errado! Tente novamente!'
                },status=500)
    else:
        # Caso não seja POST, simplesmente exibe o formulário com os dados atuais da Maquina
        form = MaquinaForm(instance=maquina)
        form = form.as_p()
    # return render(request, 'maquina/edit.html', {'form': form})
    

    return HttpResponse(form)

def list_maquina(request):
    return render(request,'maquina/list.html')

@csrf_exempt
def processar_maquina(request):
    
    draw = int(request.POST.get('draw', 0))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))

    # Ordenação
    order_column_index = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'asc')
    
    # Mapeamento do índice da coluna para o campo correspondente no banco de dados
    columns = [
        'codigo',
        'descricao',
        'apelido',
        'setor__nome',
        'tombamento',
        'area',
        'criticidade',
        'foto'
    ]
    
    order_column = columns[order_column_index]

    if order_dir == 'desc':
        order_column = '-' + order_column

    # Filtrando as máquinas (se houver busca)
    search_value = request.POST.get('search[value]', '')
    filtro_maquina = request.POST.get('maquina', '')
    filtro_criticidade = request.POST.get('criticidade', '')
    filtro_maquina_critica = request.POST.get('maquina_critica', '')
    filtro_setor = request.POST.get('setor', '')

    if request.user.area in ['producao', 'predial']:
        maquinas = Maquina.objects.filter(area=request.user.area)
    else:
        maquinas = Maquina.objects.all()

    if search_value:
        maquinas = maquinas.filter(
            Q(codigo__icontains=search_value) |
            Q(descricao__icontains=search_value) |
            Q(apelido__icontains=search_value) |
            Q(setor__nome__icontains=search_value)
        )

    if filtro_maquina:
        maquinas = maquinas.filter(id=filtro_maquina)
    if filtro_criticidade:
        maquinas = maquinas.filter(criticidade=filtro_criticidade)
    if filtro_setor:
        maquinas = maquinas.filter(setor_id=filtro_setor)
    if filtro_maquina_critica:
        if filtro_maquina_critica == 'sim':
            maquinas = maquinas.filter(maquina_critica=True)
        elif filtro_maquina_critica == 'nao':
            maquinas = maquinas.filter(maquina_critica=False)

    # Aplicando ordenação
    maquinas = maquinas.order_by(order_column)

    # Paginação
    paginator = Paginator(maquinas, length)
    maquinas_page = paginator.get_page(start // length + 1)

    data = []
    for maquina in maquinas_page:
        # print("maq-crit ",maquina.maquina_critica)
        data.append({
            'id': maquina.pk,
            'codigo': maquina.codigo,
            'descricao': maquina.descricao if maquina.descricao else 'N/A',
            'apelido': maquina.apelido if maquina.apelido else 'N/A',
            'setor': str(maquina.setor),
            'tipo': maquina.tipo if maquina.tipo else 'N/A',
            'foto': maquina.foto.url if maquina.foto else '',
            'tombamento': maquina.tombamento if maquina.tombamento else 'N/A',
            'area': maquina.get_area_display(),
            'criticidade': maquina.get_criticidade_display(),
            'maquina_critica': 'Sim' if maquina.maquina_critica else 'Não'
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': paginator.count,
        'recordsFiltered': paginator.count,
        'data': data,
    })

def list_operador(request):

    return render(request,'operador/list.html')

def add_operador(request):
    
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)

            nome = dados['nome']
            matricula = dados['matricula']
            area = request.user.area

            operador = Operador.objects.create(
                nome=nome,
                matricula=matricula,
                area=area,
                status='ativo'
            )

            return JsonResponse({'message': 'Operador criado com sucesso'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except KeyError as e:
            return JsonResponse({'error': f'Campo ausente: {str(e)}'}, status=400)
        except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=400)
        except IntegrityError:
            return JsonResponse({'error': 'Matrícula já cadastrada'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Método não permitido'}, status=405)

def edit_operador(request,pk):

    try:
        operador = get_object_or_404(Operador, pk=pk)

        if request.method == 'PUT':
            try:
                dados = json.loads(request.body)

                if operador.matricula != dados['matricula']:
                    operador.matricula = dados['matricula']
                if operador.nome != dados['nome']:
                    operador.nome = dados['nome']
                if 'area' in dados and operador.area != dados['area']:
                    operador.area = dados['area']
                operador.save()

                return JsonResponse({'message': 'Ok'}, status=200)

            except json.JSONDecodeError:
                return JsonResponse({'error': 'JSON inválido'}, status=400)
            except KeyError as e:
                return JsonResponse({'error': f'Campo ausente: {str(e)}'}, status=400)
            except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=400)
            except IntegrityError:
                return JsonResponse({'error': 'Matrícula já cadastrada'}, status=400)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        elif request.method == 'PATCH':
            try:          
                if operador.status != 'inativo':
                    operador.status = 'inativo'
                    operador.save()

                return JsonResponse({'message': 'Ok'}, status=200)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'JSON inválido'}, status=400)
            except KeyError as e:
                return JsonResponse({'error': f'Campo ausente: {str(e)}'}, status=400)
            except (ValidationError, IntegrityError) as e:
                return JsonResponse({'error': str(e)}, status=400)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

    except Http404:
        return JsonResponse({'error': 'Operador não encontrado'}, status=404)

def importar_csv_maquina(request):
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        data = pd.read_csv(csv_file)
        data = data.drop_duplicates(subset='codigo')
        
        for index, row in data.iterrows():
            # Verifica se o código já existe
            if Maquina.objects.filter(codigo=row['codigo']).exists():
                # Pula para a próxima iteração se o código já existir
                continue
            
            # Se não existir, cria a nova máquina
            setor, created = Setor.objects.get_or_create(pk=row['setor'])

            Maquina.objects.create(
                codigo=row['codigo'],
                descricao=row['descricao'],
                apelido=row['apelido'],
                tombamento=row['tombamento'] if not pd.isnull(row['tombamento']) else '',
                setor=setor,
                area=row['area'],
                criticidade=row['criticidade']   
            )

        return redirect('list_maquina')

    return render(request, 'maquina/add_emcarga.html')

def api_operadores(request):
    search = request.GET.get('search', '')
    limit = int(request.GET.get('limit', 25))

    operadores = Operador.objects.all()

    if search:
        operadores = operadores.filter(nome__icontains=search)

    operadores = list(operadores.values())
    return JsonResponse({'operadores': operadores})

def api_maquinas(request):
    """API para retornar a lista de máquinas em formato JSON."""
    search = request.GET.get('search', '')
    limit = int(request.GET.get('limit', 25))  # permite controlar o limite via querystring

    qs = Maquina.objects.filter(area='producao')

    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(descricao__icontains=search)
        )

    maquinas = list(qs.values('id', 'codigo', 'descricao')[:limit])

    return JsonResponse({'maquinas': maquinas})

def api_maquinas_list(request):
    """API para retornar a lista de mǭquinas conforme a Ç­rea do usuÇ­rio."""
    search = request.GET.get('search', '')
    limit = int(request.GET.get('limit', 500))

    if request.user.area in ['producao', 'predial']:
        qs = Maquina.objects.filter(area=request.user.area)
    else:
        qs = Maquina.objects.all()

    if search:
        qs = qs.filter(
            Q(codigo__icontains=search) |
            Q(descricao__icontains=search) |
            Q(apelido__icontains=search)
        )

    maquinas = list(qs.order_by('codigo').values('id', 'codigo', 'descricao')[:limit])

    return JsonResponse({'maquinas': maquinas})


def api_setores(request):
    """Endpoint para retornar a lista de setores em formato JSON."""
    search = request.GET.get('search', '')

    qs = Setor.objects.all()

    if search:
        qs = qs.filter(nome__icontains=search)

    setores = list(qs.values('id', 'nome')[:25])
        

    return JsonResponse({
                'message': 'success',
                'setores': setores
            })

def api_tipo_manutencao(request):
    """Endpoint para retornar a lista de tipo de manutenção em formato JSON."""
    search = request.GET.get('search', '')

    qs = InfoSolicitacao.objects.all().values('tipo_manutencao').distinct()

    if search:
        qs = qs.filter(tipo_manutencao__icontains=search)

    tipos = list(qs)   

    return JsonResponse({'message': 'success','tiposManutencao': tipos})

def api_status_execucao(request):
    """Endpoint para retornar a lista de status em formato JSON."""
    search = request.GET.get('search', '')

    qs = Execucao.objects.all().values('status').distinct()

    if search:
        qs = qs.filter(status__icontains=search)

    status = list(qs)   

    return JsonResponse({'message':'success','status': status})

def api_tarefa_rotina(request):
    """Endpoint para retornar a lista de tarefas de rotina em formato JSON."""
    search = request.GET.get('search', '')

    qs = TipoTarefas.objects.filter(status=True).values()

    if search:
        qs = qs.filter(nome__icontains=search)

    tarefas_rotina = list(qs)   

    return JsonResponse({'message':'success','tarefasRotina': tarefas_rotina})


# ─── Pedidos de Compra ────────────────────────────────────────────────────────

def list_pedido_compra(request):
    return render(request, 'pedido_compra/list.html')


@csrf_exempt
def processar_pedido_compra(request):
    draw = int(request.POST.get('draw', 0))
    start = int(request.POST.get('start', 0))
    length = int(request.POST.get('length', 10))

    order_column_index = int(request.POST.get('order[0][column]', 0))
    order_dir = request.POST.get('order[0][dir]', 'desc')

    columns = [
        'data_criacao', 'numero_pedido', 'responsavel',
        'fornecedor_codigo', 'codigo_produto', 'descricao_produto',
        'valor', 'data_aprovacao', 'data_baixa',
    ]
    order_column = columns[min(order_column_index, len(columns) - 1)]
    if order_dir == 'desc':
        order_column = '-' + order_column

    search_value = request.POST.get('search[value]', '')
    data_inicio = request.POST.get('data_inicio', '')
    data_fim = request.POST.get('data_fim', '')
    fornecedor = request.POST.get('fornecedor', '')
    responsavel = request.POST.get('responsavel', '')
    status = request.POST.get('status', '')

    pedidos = PedidoCompra.objects.all()

    if data_inicio:
        pedidos = pedidos.filter(data_criacao__gte=data_inicio)
    if data_fim:
        pedidos = pedidos.filter(data_criacao__lte=data_fim)
    if fornecedor:
        pedidos = pedidos.filter(fornecedor_codigo=fornecedor)
    if responsavel:
        pedidos = pedidos.filter(responsavel=responsavel)
    if status == 'baixado':
        pedidos = pedidos.filter(data_baixa__isnull=False)
    elif status == 'aprovado':
        pedidos = pedidos.filter(data_aprovacao__isnull=False, data_baixa__isnull=True)
    elif status == 'pendente':
        pedidos = pedidos.filter(data_aprovacao__isnull=True, data_baixa__isnull=True)

    if search_value:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=search_value) |
            Q(descricao_produto__icontains=search_value) |
            Q(fornecedor_codigo__icontains=search_value) |
            Q(responsavel__icontains=search_value) |
            Q(codigo_produto__icontains=search_value)
        )

    total_records = PedidoCompra.objects.count()
    filtered_records = pedidos.count()

    pedidos = pedidos.order_by(order_column)

    paginator = Paginator(pedidos, length)
    pedidos_page = paginator.get_page(start // length + 1)

    data = []
    for p in pedidos_page:
        if p.data_baixa:
            status_display = 'Baixado'
            status_class = 'success'
        elif p.data_aprovacao:
            status_display = 'Aprovado'
            status_class = 'primary'
        else:
            status_display = 'Pendente'
            status_class = 'warning'

        data.append({
            'data_criacao': p.data_criacao.strftime('%d/%m/%Y') if p.data_criacao else '',
            'numero_pedido': p.numero_pedido,
            'responsavel': p.responsavel or '',
            'fornecedor_codigo': p.fornecedor_codigo or '',
            'codigo_produto': p.codigo_produto or '',
            'descricao_produto': p.descricao_produto or '',
            'valor': float(p.valor),
            'data_aprovacao': p.data_aprovacao.strftime('%d/%m/%Y') if p.data_aprovacao else '',
            'data_baixa': p.data_baixa.strftime('%d/%m/%Y') if p.data_baixa else '',
            'status': status_display,
            'status_class': status_class,
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data,
    })


@csrf_exempt
def api_big_numbers_pedido_compra(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    data_inicio = request.POST.get('data_inicio', '')
    data_fim = request.POST.get('data_fim', '')
    fornecedor = request.POST.get('fornecedor', '')
    responsavel = request.POST.get('responsavel', '')
    status = request.POST.get('status', '')

    pedidos = PedidoCompra.objects.all()

    if data_inicio:
        pedidos = pedidos.filter(data_criacao__gte=data_inicio)
    if data_fim:
        pedidos = pedidos.filter(data_criacao__lte=data_fim)
    if fornecedor:
        pedidos = pedidos.filter(fornecedor_codigo=fornecedor)
    if responsavel:
        pedidos = pedidos.filter(responsavel=responsavel)
    if status == 'baixado':
        pedidos = pedidos.filter(data_baixa__isnull=False)
    elif status == 'aprovado':
        pedidos = pedidos.filter(data_aprovacao__isnull=False, data_baixa__isnull=True)
    elif status == 'pendente':
        pedidos = pedidos.filter(data_aprovacao__isnull=True, data_baixa__isnull=True)

    agg = pedidos.aggregate(
        total_valor=Sum('valor'),
        total_pedidos=Count('id'),
        ticket_medio=Avg('valor'),
    )

    fornecedores_unicos = (
        pedidos
        .exclude(fornecedor_codigo__isnull=True)
        .exclude(fornecedor_codigo='')
        .values('fornecedor_codigo')
        .distinct()
        .count()
    )

    ranking_qs = (
        pedidos
        .exclude(fornecedor_codigo__isnull=True)
        .exclude(fornecedor_codigo='')
        .values('fornecedor_codigo')
        .annotate(total=Sum('valor'), qtd=Count('id'))
        .order_by('-total')[:10]
    )

    return JsonResponse({
        'total_valor': float(agg['total_valor'] or 0),
        'total_pedidos': agg['total_pedidos'] or 0,
        'ticket_medio': float(agg['ticket_medio'] or 0),
        'fornecedores_unicos': fornecedores_unicos,
        'ranking': list(ranking_qs),
    })


def api_filtros_pedido_compra(request):
    fornecedores = list(
        PedidoCompra.objects
        .exclude(fornecedor_codigo__isnull=True)
        .exclude(fornecedor_codigo='')
        .values_list('fornecedor_codigo', flat=True)
        .distinct()
        .order_by('fornecedor_codigo')
    )
    responsaveis = list(
        PedidoCompra.objects
        .exclude(responsavel__isnull=True)
        .exclude(responsavel='')
        .values_list('responsavel', flat=True)
        .distinct()
        .order_by('responsavel')
    )
    return JsonResponse({'fornecedores': fornecedores, 'responsaveis': responsaveis})
