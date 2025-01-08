from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from django.db import transaction, IntegrityError

from .models import PlanoPreventiva, Solicitacao, SolicitacaoPreventiva
from execucao.models import InfoSolicitacao, Execucao
from cadastro.models import Operador

from datetime import datetime

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

# def inserir_ordens_preventivas_historicas():
#     # Dados fornecidos
#     historico_ordens = [
#         {"id": 1591, "maquina": 27, "setor": 5, "plano_id": 18, "descricao": "10 Meses", "area": "producao", "data": "2024-04-01 00:00:00"},
#         {"id": 1912, "maquina": 69, "setor": 1, "plano_id": 32, "descricao": "10 Meses", "area": "producao", "data": "2024-05-31 00:00:00"},
#         {"id": 1947, "maquina": 4, "setor": 1, "plano_id": 27, "descricao": "10 Meses", "area": "producao", "data": "2024-06-07 00:00:00"},
#         {"id": 2203, "maquina": 20, "setor": 5, "plano_id": 39, "descricao": "10 Meses", "area": "producao", "data": "2024-07-24 00:00:00"},
#     ]

#     # Usuário padrão para a solicitação
#     try:
#         solicitante = User.objects.get(matricula='0000')
#     except User.DoesNotExist:
#         print("Usuário com matrícula '0000' não encontrado.")
#         return

#     for ordem in historico_ordens:
#         try:
#             # Obter o plano preventivo associado
#             plano = PlanoPreventiva.objects.filter(pk=ordem['plano_id']).first()

#             if not plano:
#                 print(f'Plano não encontrado para máquina {ordem["maquina"]} na área {ordem["area"]}.')
#                 continue

#             # Verificar se a solicitação já existe
#             if Solicitacao.objects.filter(id=ordem["id"]).exists():
#                 print(f'Solicitação com ID {ordem["id"]} já existe. Pulando.')
#                 continue

#             # Converter a data para o formato correto
#             data_prevista = datetime.strptime(ordem["data"], '%Y-%m-%d').date()

#             # Criar nova solicitação
#             nova_solicitacao = Solicitacao.objects.create(
#                 id=ordem["id"],
#                 impacto_producao="baixo",
#                 maquina=plano.maquina,
#                 setor=plano.maquina.setor,
#                 solicitante=solicitante,
#                 descricao=f'Preventiva: {ordem["descricao"]}',
#                 area=ordem["area"],
#                 planejada=True,
#                 data_abertura=data_prevista,  # Ajuste aqui para incluir a data
#             )

#             print(f'Solicitação {nova_solicitacao.id} criada com sucesso.')

#         except IntegrityError:
#             print(f'Erro: A solicitação com ID {ordem["id"]} já existe.')
#         except Exception as e:
#             print(f"Erro ao criar solicitação para a máquina {ordem['maquina']}: {str(e)}")

# def atualizar_solicitacoes_preventivas():
#     # Dados fornecidos
#     # ordens_responsaveis = [
#     #     {"ordem": 4262, "operador": 23, "data_inicio": "2024-02-11 08:00:00", "data_fim": "2024-02-11 12:30:00"},
#     #     {"ordem": 4263, "operador": 23, "data_inicio": "2024-02-11 08:00:00", "data_fim": "2024-02-11 12:30:00"},
#     #     {"ordem": 4264, "operador": 23, "data_inicio": "2024-02-11 08:00:00", "data_fim": "2024-02-11 12:30:00"},
#     #     {"ordem": 4265, "operador": 4, "data_inicio": "2024-03-30 07:00:00", "data_fim": "2024-03-30 09:00:00"},
#     #     {"ordem": 4266, "operador": 4, "data_inicio": "2024-03-16 07:00:00", "data_fim": "2024-03-16 08:00:00"},
#     #     {"ordem": 4267, "operador": 22, "data_inicio": "2024-07-15 22:00:00", "data_fim": "2024-07-16 06:00:00"},
#     #     {"ordem": 4268, "operador": 4, "data_inicio": "2024-09-14 08:00:00", "data_fim": "2024-09-14 10:40:00"},
#     #     {"ordem": 4269, "operador": 22, "data_inicio": "2024-08-01 03:00:00", "data_fim": "2024-08-01 06:20:00"},
#     #     {"ordem": 4270, "operador": 22, "data_inicio": "2024-08-02 22:30:00", "data_fim": "2024-08-03 05:00:00"},
#     #     {"ordem": 4271, "operador": 22, "data_inicio": "2024-09-07 11:00:00", "data_fim": "2024-09-07 14:00:00"},
#     #     {"ordem": 4272, "operador": 22, "data_inicio": "2024-09-07 10:00:00", "data_fim": "2024-09-07 15:00:00"},
#     #     {"ordem": 4273, "operador": 22, "data_inicio": "2024-07-19 21:00:00", "data_fim": "2024-07-20 05:00:00"},
#     #     {"ordem": 4274, "operador": 4, "data_inicio": "2024-10-30 15:00:00", "data_fim": "2024-10-30 17:00:00"},
#     #     {"ordem": 4275, "operador": 4, "data_inicio": "2024-10-30 15:00:00", "data_fim": "2024-10-30 17:00:00"},
#     #     {"ordem": 4276, "operador": 4, "data_inicio": "2024-10-20 15:00:00", "data_fim": "2024-10-20 17:00:00"},
#     # ]

#     ordens_responsaveis = [
#         {"id": 1591, "operador":4, "maquina": 27, "setor": 5, "plano_id": 18, "descricao": "10 Meses", "area": "producao", "datainicio": "2024-09-14 08:00:00", 'datafim':"2024-09-14 10:40:00", 'status_andamento':'em_execucao'},
#         {"id": 1912, "operador":6, "maquina": 69, "setor": 1, "plano_id": 32, "descricao": "10 Meses", "area": "producao", "datainicio": "2024-08-01 03:00:00", 'datafim':"2024-08-01 06:20:00",'status_andamento':'em_execucao'},
#         {"id": 1947, "operador":6, "maquina": 4, "setor": 1, "plano_id": 27, "descricao": "10 Meses", "area": "producao", "datainicio": "2024-08-02 22:30:00", 'datafim':"2024-08-03 05:00:00",'status_andamento':'em_execucao'},
#         {"id": 2203, "operador":7, "maquina": 20, "setor": 5, "plano_id": 39, "descricao": "10 Meses", "area": "producao", "datainicio": "2024-10-14 14:00:00", 'datafim':"2024-10-14 18:00:00",'status_andamento':'em_execucao'},
#     ]
    
#     with transaction.atomic():
#         for ordem in ordens_responsaveis:
#             try:
#                 # Buscar a solicitação pela ordem
#                 solicitacao = Solicitacao.objects.get(id=ordem["id"])
#                 solicitacao.status_andamento = ordem['status_andamento']

#                 # # Buscar o operador responsável
#                 operador = Operador.objects.get(id=ordem["operador"])
#                 plano = PlanoPreventiva.objects.get(id=ordem["plano_id"])

#                 # # Atualizar a solicitação
#                 solicitacao.atribuido = operador
#                 solicitacao.programacao = solicitacao.data_abertura
#                 solicitacao.status = "aprovar"  # Atualizar o status para "aprovar"
#                 solicitacao.nivel_prioridade = 'baixo'
#                 solicitacao.status_andamento = 'em_execucao'
#                 data_inicio = datetime.strptime(ordem["datainicio"], "%Y-%m-%d %H:%M:%S")
#                 data_fim = datetime.strptime(ordem["datafim"], "%Y-%m-%d %H:%M:%S")

#                 # Criar a execução
#                 execucao = Execucao.objects.create(
#                     ordem=solicitacao,
#                     n_execucao=1,
#                     data_inicio=data_inicio,
#                     data_fim=data_fim,
#                     observacao="Histórico de execução de preventiva",
#                     status="em_execucao",
#                     che_maq_parada=False,
#                     exec_maq_parada=False,
#                     apos_exec_maq_parada=False,
#                 )

#                 execucao.operador.add(operador)

#                 execucao.save()
#                 solicitacao.save()

#                 InfoSolicitacao.objects.update_or_create(
#                     solicitacao=solicitacao,
#                     defaults={'area_manutencao': 'mecanica', 'tipo_manutencao':'preventiva_programada'}
#                 )

#                 SolicitacaoPreventiva.objects.create(
#                     data=solicitacao.data_abertura,
#                     ordem=solicitacao,
#                     plano=plano
#                 )

#                 print(f"Solicitação {solicitacao.id} atualizada com sucesso.")
#             except Solicitacao.DoesNotExist:
#                 print(f"Solicitação com ID {ordem['ordem']} não encontrada.")
#             except Operador.DoesNotExist:
#                 print(f"Operador com ID {ordem['responsavel_id']} não encontrado.")
#             except Exception as e:
#                 print(f"Erro ao atualizar a solicitação {ordem['ordem']}: {e}")


