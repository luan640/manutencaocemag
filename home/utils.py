from cadastro.models import Operador
from execucao.models import Execucao, MaquinaParada
from funcionario.models import Funcionario

from collections import defaultdict

def ultima_execucao(id_solicitacao):

    id_ult_execucao = Execucao.objects.filter(ordem_id=id_solicitacao).order_by('-n_execucao').first()

    return id_ult_execucao

def operadores_all(area):

    operadores = Operador.objects.filter(area=area, status='ativo')

    return operadores

def maquinas_paradas():
    maquinas_paradas = (
        MaquinaParada.objects
        .filter(data_fim=None)
        .select_related('ordem__maquina')
    )
    
    maquinas_com_ordens = defaultdict(list)

    for maq_parada in maquinas_paradas:
        ordem = maq_parada.ordem
        maquina = ordem.maquina

        # Adiciona o objeto da ordem (não string!)
        maquinas_com_ordens[maquina].append(ordem)

    return maquinas_com_ordens

def buscar_telefone(matricula):

    funcionario = Funcionario.objects.get(matricula=matricula)

    return funcionario.telefone