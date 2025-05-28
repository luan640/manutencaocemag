from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from django.db import transaction, IntegrityError

from .models import PlanoPreventiva, Solicitacao, SolicitacaoPreventiva
from execucao.models import InfoSolicitacao, Execucao
from cadastro.models import Operador

from datetime import datetime
import csv

User = get_user_model()


def verificar_abertura_solicitacoes_preventivas():
    hoje = timezone.now().date()
    solicitante = User.objects.get(matricula='0000')
    planos = PlanoPreventiva.objects.filter(ativo=True)
    
    for plano in planos:
        # Verifica se a data_base está definida, caso contrário, usa a data de criação do plano
        data_base = plano.data_base 
        
        if plano.data_base:

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

def inserir_ordens_preventivas_historicas_arquivo(file_path):
    
    """
    Insere ordens preventivas históricas a partir de um arquivo CSV.
    """
    
    # Usuário padrão para a solicitação
    try:
        solicitante = User.objects.get(matricula='0000')
    except User.DoesNotExist:
        print("Usuário com matrícula '0000' não encontrado.")
        return

    # Lê os dados do arquivo CSV
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                # Obter os dados da linha
                ordem_id = int(row['ordem'].replace('.',''))
                plano_id = int(row['plano_id'])
                # descricao = row['descricao']
                area = 'producao'
                data_abertura = row['dataabertura']

                # Obter o plano preventivo associado
                plano = PlanoPreventiva.objects.filter(pk=plano_id).first()

                # Verificar se a solicitação já existe
                if Solicitacao.objects.filter(id=ordem_id).exists():
                    print(f'Solicitação com ID {ordem_id} já existe. Pulando.')
                    continue

                # Converter a data para o formato correto
                data_abertura = datetime.strptime(data_abertura, '%Y-%m-%d %H:%M:%S').date()

                # Criar nova solicitação
                nova_solicitacao = Solicitacao.objects.create(
                    id=ordem_id,
                    impacto_producao="baixo",
                    maquina=plano.maquina,
                    setor=plano.maquina.setor,
                    solicitante=solicitante,
                    descricao=f'Preventiva: {plano.nome}',
                    area=area,
                    planejada=True,
                    data_abertura=data_abertura,  # Ajuste aqui para incluir a data
                )

                print(f'Solicitação {nova_solicitacao.id} criada com sucesso.')

            except IntegrityError:
                print(f'Erro: A solicitação com ID {ordem_id} já existe.')

def atualizar_solicitacoes_preventivas(file_path):
    
    with transaction.atomic():
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    # Buscar a solicitação pela ordem
                    solicitacao = Solicitacao.objects.get(id=row["ordem"])

                    # # Buscar o operador responsável
                    operador = Operador.objects.get(id=row["operador"])
                    plano = PlanoPreventiva.objects.get(id=row["plano_id"])

                    # # Atualizar a solicitação
                    solicitacao.atribuido = operador
                    solicitacao.programacao = solicitacao.data_abertura
                    solicitacao.status = "aprovar"  # Atualizar o status para "aprovar"
                    solicitacao.nivel_prioridade = 'baixo'
                    solicitacao.status_andamento = 'em_espera'
                    data_inicio = datetime.strptime(row["datainicio"], "%Y-%m-%d %H:%M:%S")
                    data_fim = datetime.strptime(row["datafim"], "%Y-%m-%d %H:%M:%S")

                    # Criar a execução
                    execucao = Execucao.objects.create(
                        ordem=solicitacao,
                        n_execucao=1,
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                        observacao="Histórico de execução de preventiva",
                        status="em_espera",
                        che_maq_parada=False,
                        exec_maq_parada=False,
                        apos_exec_maq_parada=False,
                    )

                    execucao.operador.add(operador)

                    execucao.save()
                    solicitacao.save()

                    InfoSolicitacao.objects.update_or_create(
                        solicitacao=solicitacao,
                        defaults={'area_manutencao': 'mecanica', 'tipo_manutencao':'preventiva_programada'}
                    )

                    SolicitacaoPreventiva.objects.create(
                        data=solicitacao.data_abertura,
                        ordem=solicitacao,
                        plano=plano
                    )

                    print(f"Solicitação {solicitacao.id} atualizada com sucesso.")
                except Solicitacao.DoesNotExist:
                    print(f"Solicitação com ID {row['ordem']} não encontrada.")
                except Operador.DoesNotExist:
                    print(f"Operador com ID {row['responsavel_id']} não encontrado.")
                except Exception as e:
                    print(f"Erro ao atualizar a solicitação {row['ordem']}: {e}")
