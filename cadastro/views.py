from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Q


from .forms import MaquinaForm, AddOperadorForm
from .models import Maquina, Operador, Setor
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

    if request.user.is_staff:
        maquinas = Maquina.objects.all()
    else:
        maquinas = Maquina.objects.filter(area=request.user.area)

    if search_value:
        maquinas = maquinas.filter(
            codigo__icontains=search_value
        )

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

    if request.user.tipo_acesso == 'administrador' and not request.user.is_staff:
        operadores = Operador.objects.filter(area=request.user.area)
    else:
        operadores = Operador.objects.all()

    if search:
        operadores = operadores.filter(nome__icontains=search)

    operadores = list(operadores.values()[:limit])
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
