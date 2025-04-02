from django.urls import path
from .views import excluir_plano_preventiva,preventivas_em_aberto,ultimas_preventivas,calcular_manutencoes_semanais,planejamento_anual,programacao,ordens_programadas,criar_plano_preventiva,criar_tarefa_preventiva,criar_solicitacao_preventiva,list_preventivas,editar_plano_preventiva
from . import views

urlpatterns = [
    path('preventiva/', list_preventivas, name='list_preventivas'),

    path('plano-preventiva/criar/<int:pk_maquina>/', criar_plano_preventiva, name='criar_plano_preventiva'),
    path('plano-preventiva/edit/<int:pk>/', editar_plano_preventiva, name='editar_plano_preventiva'),
    path('plano-preventiva/excluir/<int:pk>/', excluir_plano_preventiva, name='excluir_plano_preventiva'),

    path('tarefa-preventiva/criar/', criar_tarefa_preventiva, name='criar_tarefa_preventiva'),
    path('solicitacao-preventiva/criar/', criar_solicitacao_preventiva, name='criar_solicitacao_preventiva'),

    path('programacao/ordens-programadas/<str:area>/', ordens_programadas, name='ordens_programadas'),
    path('programacao/<str:area>/', programacao, name='programacao'),

    path('planejamento-anual/', planejamento_anual, name='planejamento_anual'),
    path('manutencoes-semana/', calcular_manutencoes_semanais, name='manutencoes_semanais'),

    path('ultimas-preventivas/', ultimas_preventivas, name='ultimas_preventivas'),
    path('preventivas-aberto/', preventivas_em_aberto, name='preventivas_em_aberto'),

    path('get-maquinas-preventiva/', views.get_maquinas_preventiva, name='get_maquinas_preventiva'),
    path('buscar-historico/', views.buscar_historico, name='buscar_historico'),

    path('historico-preventiva/', views.historico_preventivas, name='historico_preventivas'),

    # modificar a coluna maquina_critica da tabela maquina para as maquinas que possuem plano de preventiva ativo
    path('maquina-critica/',views.maquina_critica, name='maquina_critica'),


]
