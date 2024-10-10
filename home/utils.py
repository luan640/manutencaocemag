from cadastro.models import Operador
from execucao.models import Execucao, MaquinaParada
from funcionario.models import Funcionario

from collections import defaultdict

def ultima_execucao(id_solicitacao):

    id_ult_execucao = Execucao.objects.filter(ordem_id=id_solicitacao).order_by('-n_execucao').first()

    return id_ult_execucao

def operadores_all(area):

    operadores = Operador.objects.filter(area=area)

    return operadores

def maquinas_paradas():
    # Filtra as máquinas que estão paradas (data_fim=None)
    maquinas_paradas = MaquinaParada.objects.filter(data_fim=None)
    
    # Dicionário para armazenar as ordens associadas a cada máquina
    maquinas_com_ordens = defaultdict(list)

    for maquina_parada in maquinas_paradas:
        maquina = maquina_parada.ordem.maquina
        maquinas_com_ordens[maquina].append(maquina_parada.ordem)

    return maquinas_com_ordens

def buscar_telefone(matricula):

    funcionario = Funcionario.objects.get(matricula=matricula)

    return funcionario.telefone