from django.urls import path
from .views import criar_plano_preventiva,criar_tarefa_preventiva,criar_solicitacao_preventiva,list_preventivas,editar_plano_preventiva

urlpatterns = [
    path('preventiva', list_preventivas, name='list_preventivas'),

    path('plano-preventiva/criar/<int:pk_maquina>/', criar_plano_preventiva, name='criar_plano_preventiva'),
    path('plano-preventiva/edit/<int:pk>/', editar_plano_preventiva, name='editar_plano_preventiva'),
    
    path('tarefa-preventiva/criar/', criar_tarefa_preventiva, name='criar_tarefa_preventiva'),
    path('solicitacao-preventiva/criar/', criar_solicitacao_preventiva, name='criar_solicitacao_preventiva'),
]
