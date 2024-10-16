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

# def proximas_preventivas(request):

