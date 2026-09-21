import json
from functools import wraps

from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from cadastro.models import Maquina
from funcionario.models import Funcionario

from .forms import SolicitacaoForm, SolicitacaoPredialForm

AREAS = ('producao', 'predial')
DESCRICAO_MAX = 2000


def _ip_cliente(request):
    # Atrás do proxy do Render o IP real vem no X-Forwarded-For.
    encaminhado = request.META.get('HTTP_X_FORWARDED_FOR')
    if encaminhado:
        return encaminhado.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconhecido')


def endpoint_publico(metodos, limite, janela=60):
    """Endpoint sem login: libera CORS/CSRF e aplica rate limit por IP."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == 'OPTIONS':
                resposta = HttpResponse(status=204)
            elif request.method not in metodos:
                resposta = JsonResponse({'error': 'Método não permitido.'}, status=405)
                resposta['Allow'] = ', '.join(metodos)
            else:
                chave = f'api_publica:{view.__name__}:{_ip_cliente(request)}'
                cache.add(chave, 0, janela)
                try:
                    total = cache.incr(chave)
                except ValueError:
                    cache.set(chave, 1, janela)
                    total = 1

                if total > limite:
                    resposta = JsonResponse(
                        {'error': 'Muitas requisições. Tente novamente em instantes.'}, status=429
                    )
                else:
                    resposta = view(request, *args, **kwargs)

            resposta['Access-Control-Allow-Origin'] = '*'
            resposta['Access-Control-Allow-Methods'] = ', '.join(metodos) + ', OPTIONS'
            resposta['Access-Control-Allow-Headers'] = 'Content-Type'
            return resposta

        return csrf_exempt(wrapper)
    return decorator


def _ler_dados(request):
    if request.content_type == 'application/json':
        try:
            dados = json.loads(request.body or b'{}')
        except (ValueError, UnicodeDecodeError):
            return None
        return dados if isinstance(dados, dict) else None
    return request.POST.dict()


@endpoint_publico(metodos=('GET',), limite=120)
def listar_maquinas(request):
    area = request.GET.get('area')
    busca = request.GET.get('search', '').strip()

    if area and area not in AREAS:
        return JsonResponse({'error': "area deve ser 'producao' ou 'predial'."}, status=400)

    try:
        limit = min(max(int(request.GET.get('limit', 100)), 1), 500)
        offset = max(int(request.GET.get('offset', 0)), 0)
    except ValueError:
        return JsonResponse({'error': 'limit e offset devem ser números inteiros.'}, status=400)

    maquinas = Maquina.objects.select_related('setor').order_by('codigo', 'id')

    if area:
        maquinas = maquinas.filter(area=area)

    if busca:
        maquinas = maquinas.filter(
            Q(codigo__icontains=busca) | Q(descricao__icontains=busca) | Q(apelido__icontains=busca)
        )

    total = maquinas.count()
    resultados = [
        {
            'id': maquina.id,
            'codigo': maquina.codigo,
            'descricao': maquina.descricao,
            'area': maquina.area,
            'setor_id': maquina.setor_id,
            'setor': maquina.setor.nome,
        }
        for maquina in maquinas[offset:offset + limit]
    ]

    return JsonResponse({'count': total, 'limit': limit, 'offset': offset, 'results': resultados})


@endpoint_publico(metodos=('POST',), limite=20)
def criar_ordem(request):
    dados = _ler_dados(request)
    if dados is None:
        return JsonResponse({'error': 'Corpo da requisição inválido. Envie um JSON válido.'}, status=400)

    erros = {}

    matricula = str(dados.get('matricula') or '').strip()
    area = dados.get('area')
    descricao = str(dados.get('descricao') or '').strip()

    if not matricula:
        erros['matricula'] = ['Campo obrigatório.']
    if area not in AREAS:
        erros['area'] = ["Informe 'producao' ou 'predial'."]
    if not descricao:
        erros['descricao'] = ['Campo obrigatório.']
    elif len(descricao) > DESCRICAO_MAX:
        erros['descricao'] = [f'Máximo de {DESCRICAO_MAX} caracteres.']

    solicitante = None
    if matricula:
        solicitante = Funcionario.objects.filter(matricula=matricula, is_active=True).first()
        if solicitante is None:
            erros['matricula'] = ['Matrícula não encontrada ou inativa.']

    if erros:
        return JsonResponse({'errors': erros}, status=400)

    Formulario = SolicitacaoForm if area == 'producao' else SolicitacaoPredialForm
    campos = [campo for campo in Formulario.Meta.fields if campo not in ('video', 'descricao')]
    entrada = {campo: dados[campo] for campo in campos if campo in dados}
    entrada['descricao'] = descricao

    setor_vazio = entrada.get('setor') in (None, '')
    if setor_vazio and entrada.get('maquina') not in (None, ''):
        try:
            setor_da_maquina = Maquina.objects.filter(pk=entrada['maquina']).values_list('setor_id', flat=True).first()
        except (ValueError, TypeError):
            setor_da_maquina = None
        if setor_da_maquina:
            entrada['setor'] = setor_da_maquina
            setor_vazio = False

    form = Formulario(entrada)

    if not form.is_valid():
        erros = {campo: [str(erro) for erro in lista] for campo, lista in form.errors.items()}
        if setor_vazio and 'setor' in erros:
            erros['setor'] = ['Informe o setor ou uma máquina válida para que ele seja calculado.']
        return JsonResponse({'errors': erros}, status=400)

    maquina = form.cleaned_data.get('maquina')
    if maquina and maquina.area != area:
        return JsonResponse({'errors': {'maquina': ['Máquina não pertence à área informada.']}}, status=400)

    solicitacao = form.save(commit=False)
    solicitacao.solicitante = solicitante
    solicitacao.area = area
    solicitacao.save()

    return JsonResponse(
        {
            'id': solicitacao.pk,
            'area': solicitacao.area,
            'status_andamento': solicitacao.status_andamento,
            'data_abertura': solicitacao.data_abertura.isoformat(),
        },
        status=201,
    )
