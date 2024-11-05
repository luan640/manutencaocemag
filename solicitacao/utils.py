from django.contrib.auth.models import User
from django.utils.timezone import now, timedelta
from django.contrib.auth import get_user_model

import random

from solicitacao.models import Solicitacao
from cadastro.models import Maquina, Setor

User = get_user_model()

def criar_solicitacoes_aleatorias(qtd):
    """
    Cria 'qtd' solicitações aleatórias para a área de produção.
    """
    try:
        # Obter todas as máquinas e usuários disponíveis
        maquinas_producao = list(Maquina.objects.filter(area='producao'))
        usuarios = list(User.objects.all())
        setores = list(Setor.objects.all())

        if not maquinas_producao or not usuarios:
            raise Exception("Não há máquinas ou usuários disponíveis.")

        for _ in range(qtd):
            maquina = random.choice(maquinas_producao)  # Escolhe uma máquina aleatória
            usuario = random.choice(usuarios)  # Escolhe um usuário aleatório
            setor = random.choice(setores) 
            descricao = f"Solicitação para {maquina.codigo} - {random.randint(1, 100)}"

            # Criação da solicitação
            solicitacao = Solicitacao.objects.create(
                setor=setor,
                maquina=maquina,
                descricao=descricao,
                maq_parada=random.choice([True,False]),
                area='producao',
                solicitante=usuario,
                data_abertura=now() - timedelta(days=random.randint(0, 30)),
                status_andamento=random.choice(['aguardando_atendimento']),
                impacto_producao=random.choice(['alto','medio','baixo'])

            )
            print(f"Solicitação criada.")

    except Exception as e:
        print(f"Erro ao criar solicitações: {e}")
