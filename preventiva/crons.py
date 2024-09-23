from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import PlanoPreventiva, Solicitacao, SolicitacaoPreventiva

User = get_user_model()

def verificar_abertura_solicitacoes_preventivas():
    hoje = timezone.now().date()
    solicitante = User.objects.get(matricula='4357')
    planos = PlanoPreventiva.objects.all()

    # Defina o número de dias de antecedência para a abertura
    dias_antecedencia = 15

    for plano in planos:
        # Verifica a última solicitação criada para este plano específico
        ultima_solicitacao = SolicitacaoPreventiva.objects.filter(plano=plano).order_by('-data').first()

        if ultima_solicitacao:
            # Calcula a data de vencimento (próxima execução) baseada na última solicitação
            data_vencimento = ultima_solicitacao.data + timedelta(days=plano.periodicidade)
        else:
            # Se não há solicitações anteriores, calcula a primeira data de vencimento baseada na criação do plano
            # Supondo que hoje seja a data de criação do plano
            data_vencimento = hoje + timedelta(days=plano.periodicidade)

        # Calcula a data de abertura (15 dias antes da data de vencimento)
        data_abertura = data_vencimento - timedelta(days=dias_antecedencia)

        # Exceção para periodicidade curta:
        # Se a periodicidade é menor ou igual a 15 dias, ajusta para abrir a solicitação no dia de vencimento
        if plano.periodicidade <= dias_antecedencia:
            data_abertura = hoje

        # Verifica se hoje é o dia de abertura e se não foi criada uma solicitação recentemente
        if hoje >= data_abertura:
            # Verifica se já existe uma solicitação aberta hoje para evitar duplicatas
            solicitacao_recente = SolicitacaoPreventiva.objects.filter(plano=plano, data=hoje).exists()

            if not solicitacao_recente:
                # Cria a nova solicitação
                nova_solicitacao = Solicitacao.objects.create(
                    impacto_producao='baixo',
                    maquina=plano.maquina,
                    setor=plano.maquina.setor,
                    solicitante=solicitante,
                    descricao=f'Preventiva: {plano.nome}',
                    area=plano.maquina.area,
                    planejada=True,
                )

                # Cria a execução da preventiva associada à solicitação
                SolicitacaoPreventiva.objects.create(
                    ordem=nova_solicitacao,
                    plano=plano,
                    data=hoje
                )
