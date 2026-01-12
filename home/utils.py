from cadastro.models import Operador
from execucao.models import Execucao, MaquinaParada
from funcionario.models import Funcionario

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
    
    maquinas_com_ordens = {}

    for maq_parada in maquinas_paradas:
        ordem = maq_parada.ordem
        maquina = ordem.maquina

        if maquina not in maquinas_com_ordens:
            maquinas_com_ordens[maquina] = {
                'ordens': [],
                'data_inicio': maq_parada.data_inicio,
            }

        # Adiciona o objeto da ordem (n?o string!)
        maquinas_com_ordens[maquina]['ordens'].append(ordem)

        data_inicio_atual = maquinas_com_ordens[maquina]['data_inicio']
        if maq_parada.data_inicio and (data_inicio_atual is None or maq_parada.data_inicio < data_inicio_atual):
            maquinas_com_ordens[maquina]['data_inicio'] = maq_parada.data_inicio

    return maquinas_com_ordens

def buscar_telefone(matricula):

    funcionario = Funcionario.objects.get(matricula=matricula)

    return funcionario.telefone
