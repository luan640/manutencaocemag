from django.urls import path
from . import views
from .views import (
    historico_execucao,
    execucao_data,
    base_maquina_parada,
    editar_maquina_parada,
)

urlpatterns = [
    path('historico/', historico_execucao, name='historico_execucao'),
    path('historico/processa-historico/', execucao_data, name='execucao_data'),
    path('maquina-parada/', base_maquina_parada, name='base_maquina_parada'),
    path('maquina-parada/<int:maquinaparada_id>/editar/', editar_maquina_parada, name='editar_maquina_parada'),
]
