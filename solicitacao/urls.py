from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views
from execucao.views import criar_execucao, criar_execucao_predial, editar_solicitacao
from solicitacao.views import get_planos_preventiva

urlpatterns = [
    path('criar-solicitacao/', views.criar_solicitacao, name='criar_solicitacao'),
    path('ajax/get-maquinas/', views.get_maquina_by_setor, name='get_maquina_by_setor'),
    path('ajax/get-maquinas-by-eq-falha/', views.get_maquina_by_eq_em_falha, name='get_maquina_by_eq_em_falha'),
    path('ajax/get-all-maquinas/', views.get_maquinas, name='get_maquinas'),
    path('ajax/get-all-setores/', views.get_setores, name='get_setores'),

    path('api/planos-preventiva/<int:maquina_id>/', get_planos_preventiva, name='get_planos_preventiva'),

    path('criar-solicitacao-predial/', views.criar_solicitacao_predial, name='criar_solicitacao_predial'),
    path('criar-tarefa-rotina/', views.tarefa_rotina, name='tarefa_rotina'),

    path('execucao/producao/<int:solicitacao_id>/', criar_execucao, name='criar_execucao'),
    path('execucao/predial/<int:solicitacao_id>/', criar_execucao_predial, name='criar_execucao_predial'),

    path('atualizar-status-maq-parada/', views.atualizar_status_maq_parada, name='atualizar_status_maq_parada'),

    path('filtrar-maquinas/', views.filtrar_maquinas_por_setor, name='filtrar_maquinas_por_setor'),

    path('solicitacao-sucesso/<str:area>/', views.solicitacao_sucesso, name='solicitacao_sucesso'),

    path('editar-ordem-inicial/<int:solicitacao_id>/', editar_solicitacao, name='editar_solicitacao'),

    path('satisfacao/<int:ordem_id>/', views.pagina_satisfacao, name='pagina_satisfacao'),
    path('satisfacao/<int:ordem_id>/responder/', views.processar_satisfacao, name='processar_satisfacao'),

    path('gerar-solicitacoes/<int:qtd>/', views.gerar_solicitacoes, name='gerar_solicitacoes'),

    path('executar-tarefa-rotina/', views.criar_execucao_rotina, name='criar_execucao_rotina'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)