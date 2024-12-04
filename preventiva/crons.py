from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import PlanoPreventiva, Solicitacao, SolicitacaoPreventiva
from execucao.models import InfoSolicitacao

User = get_user_model()

def verificar_abertura_solicitacoes_preventivas():
    hoje = timezone.now().date()
    solicitante = User.objects.get(matricula='0000')
    planos = PlanoPreventiva.objects.filter(ativo=True)
    
    for plano in planos:
        # Verifica se a data_base está definida, caso contrário, usa a data de criação do plano
        data_base = plano.data_base if plano.data_base else plano.created_at.date()

        # Calcula a data de vencimento com base na data_base
        data_vencimento = data_base + timedelta(days=plano.periodicidade)

        # Calcula a data de abertura com base na antecedência configurada
        dias_antecedencia = plano.dias_antecedencia
        data_abertura = data_vencimento - timedelta(days=dias_antecedencia)

        # Ajuste para periodicidade curta: abre no mesmo dia se a periodicidade for menor ou igual à antecedência
        if plano.periodicidade <= dias_antecedencia:
            data_abertura = hoje

        # Verifica se hoje é o dia de abertura e se não existe solicitação aberta hoje
        if hoje >= data_abertura:
            solicitacao_recente = SolicitacaoPreventiva.objects.filter(plano=plano, data=hoje).exists()
            
            if not solicitacao_recente:

                # Cria uma nova solicitação preventiva
                nova_solicitacao = Solicitacao.objects.create(
                    impacto_producao='baixo',
                    maquina=plano.maquina,
                    setor=plano.maquina.setor,
                    solicitante=solicitante,
                    descricao=f'Preventiva: {plano.nome}',
                    area=plano.maquina.area,
                    planejada=True,
                )

                # Cria a solicitação preventiva associada
                SolicitacaoPreventiva.objects.create(
                    ordem=nova_solicitacao,
                    plano=plano,
                    data=hoje
                )

                # Cria o registro de informações da solicitação
                InfoSolicitacao.objects.create(
                    solicitacao=nova_solicitacao,
                    tipo_manutencao='preventiva_programada',
                )

                # Atualiza a data_base para a data em que a ordem foi criada
                plano.data_base = hoje
                plano.save()