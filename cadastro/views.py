from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.http import JsonResponse

from .forms import MaquinaForm, AddOperadorForm
from .models import Maquina, Operador, Setor

import pandas as pd

def criar_maquina(request):
    if request.method == 'POST':
        form = MaquinaForm(request.POST, request.FILES)
        if form.is_valid():

            maquina = form.save(commit=False)  
            maquina.area = request.user.area 
            maquina.save()  
            
            return redirect('list_maquina')
    else:
        form = MaquinaForm()
    return render(request, 'maquina/add.html', {'form': form})

def edit_maquina(request, pk):
    # Obtém a instância de Maquina correspondente ao 'pk' ou retorna 404 se não existir
    maquina = get_object_or_404(Maquina, pk=pk)
    
    if request.method == 'POST':
        # Carrega os dados POST no formulário, junto com os arquivos (foto, por exemplo)
        form = MaquinaForm(request.POST, request.FILES, instance=maquina)
        
        if form.is_valid():
            # Salva o formulário e atualiza a instância da Maquina
            form.save()
            return redirect('list_maquina')  # Redireciona para a lista de máquinas ou para outra página
    else:
        # Caso não seja POST, simplesmente exibe o formulário com os dados atuais da Maquina
        form = MaquinaForm(instance=maquina)
    
    return render(request, 'maquina/edit.html', {'form': form})

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
        'foto',
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
        data.append({
            'id': maquina.pk,
            'codigo': maquina.codigo,
            'descricao': maquina.descricao,
            'apelido': maquina.apelido,
            'setor': str(maquina.setor),
            'foto': maquina.foto.url if maquina.foto else '',
            'tombamento': maquina.tombamento,
            'area': maquina.get_area_display(),
            'criticidade': maquina.get_criticidade_display(),
        })

    return JsonResponse({
        'draw': draw,
        'recordsTotal': paginator.count,
        'recordsFiltered': paginator.count,
        'data': data,
    })

def list_operador(request):

    operadores = Operador.objects.all()

    return render(request,'operador/list.html', {'operadores':operadores})

def add_operador(request):
    
    if request.method == 'POST':
        form = AddOperadorForm(request.POST)  
        if form.is_valid():
            
            operador = form.save(commit=False)
            operador.status = 'ativo'

            operador.save()  
            
            return redirect('list_operador')  
        else:
            print(form.errors)
    else:
        form = AddOperadorForm()  

    return render(request, 'operador/add.html', {'form': form})

def edit_operador(request,pk):

    operador = get_object_or_404(Operador, pk=pk)

    if request.method == 'POST':

        form = AddOperadorForm(request.POST, instance=operador)

        if form.is_valid():

            form.save()

            return redirect('list_operador')
        else:
            print(form.errors)
    else:
        form = AddOperadorForm(instance=operador)

    return render(request, 'operador/edit.html', {'form':form})


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
            setor, created = Setor.objects.get_or_create(pk=row['setor_id'])

            Maquina.objects.create(
                codigo=row['codigo'],
                descricao=row['descricao'],
                apelido=row['apelido'],
                tombamento=row['tombamento'] if not pd.isnull(row['tombamento']) else '',
                setor=setor,
                area='producao',
                criticidade='c'   
            )

        return redirect('list_maquina')

    return render(request, 'maquina/add_emcarga.html')


