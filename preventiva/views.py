from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.forms import formset_factory

from .models import PlanoPreventiva, TarefaPreventiva
from .forms import PlanoPreventivaForm, TarefaPreventivaForm, SolicitacaoPreventivaForm, TarefaPreventivaFormSet
from cadastro.models import Maquina

def criar_plano_preventiva(request, pk_maquina):
    maquina = get_object_or_404(Maquina, pk=pk_maquina)  # Obtém a máquina específica

    if request.method == 'POST':
        # Passa a máquina para o formulário, mas não permite que o usuário a edite
        plano_form = PlanoPreventivaForm(request.POST)
        
        if plano_form.is_valid():
            plano = plano_form.save(commit=False)  # Não salva ainda para associar a máquina
            plano.maquina = maquina  # Associa a máquina ao plano
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

            return redirect('list_preventivas')
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
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        draw = int(request.GET.get('draw', 0))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))

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

        preventivas = PlanoPreventiva.objects.all()
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

        return JsonResponse({
            'draw': draw,
            'recordsTotal': paginator.count,
            'recordsFiltered': paginator.count,
            'data': data,
        })

    return render(request, 'visualizacao/list.html')

def editar_plano_preventiva(request, pk):
    plano = get_object_or_404(PlanoPreventiva, pk=pk)

    if request.method == 'POST':
        plano_form = PlanoPreventivaForm(request.POST, instance=plano)
        tarefa_formset = TarefaPreventivaFormSet(request.POST, queryset=TarefaPreventiva.objects.filter(plano=plano))

        if plano_form.is_valid() and tarefa_formset.is_valid():
            plano = plano_form.save()

            # Salva as tarefas existentes
            for tarefa in tarefa_formset.save(commit=False):
                tarefa.plano = plano
                tarefa.save()

            tarefa_formset.save_m2m()

            # Adiciona novas tarefas enviadas fora do FormSet padrão
            tarefas_novas = []
            for key in request.POST:
                if key.startswith('tarefas'):
                    parts = key.split('[')
                    index = int(parts[1].split(']')[0])
                    field = parts[2].split(']')[0]

                    while len(tarefas_novas) <= index:
                        tarefas_novas.append({})

                    tarefas_novas[index][field] = request.POST[key]

            # Salva as novas tarefas
            for tarefa in tarefas_novas:
                descricao = tarefa.get('descricao')
                responsabilidade = tarefa.get('responsabilidade')

                if descricao and responsabilidade:
                    TarefaPreventiva.objects.create(
                        plano=plano,
                        descricao=descricao,
                        responsabilidade=responsabilidade
                    )

            return redirect('list_preventivas')
        else:
            print('Erros no plano_form:', plano_form.errors)
            print('Erros no tarefa_formset:', tarefa_formset.errors)

    else:
        plano_form = PlanoPreventivaForm(instance=plano)
        tarefa_formset = TarefaPreventivaFormSet(queryset=TarefaPreventiva.objects.filter(plano=plano))

    return render(request, 'plano/edit.html', {
        'plano_form': plano_form,
        'tarefa_formset': tarefa_formset,
    })
