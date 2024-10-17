from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import PlanoPreventiva, Solicitacao, SolicitacaoPreventiva
from execucao.models import InfoSolicitacao

User = get_user_model()

def verificar_abertura_solicitacoes_preventivas():
    hoje = timezone.now().date()
    solicitante = User.objects.get(matricula='4357')
    planos = PlanoPreventiva.objects.all()

    for plano in planos:
        # Obtém o número de dias de antecedência do plano
        dias_antecedencia = plano.dias_antecedencia

        # Verifica a última solicitação criada para este plano específico
        ultima_solicitacao = SolicitacaoPreventiva.objects.filter(plano=plano).order_by('-data').first()

        if ultima_solicitacao:
            # Calcula a data de vencimento baseada na última solicitação
            data_vencimento = ultima_solicitacao.data + timedelta(days=plano.periodicidade)
        else:
            # Se não houver solicitações anteriores, usa a criação do plano como referência
            data_vencimento = hoje + timedelta(days=plano.periodicidade)

        # Calcula a data de abertura baseada na antecedência configurada
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