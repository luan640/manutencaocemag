from django.urls import path
from .views import *

urlpatterns = [
    path('maquina/adicionar/', criar_maquina, name='criar_maquina'),
    path('maquina/editar/<int:pk>/', edit_maquina, name='edit_maquina'),
    path('maquina/list', list_maquina, name='list_maquina'),
    path('maquina/processar', processar_maquina, name='processar_maquina'),
    path('maquina/add-carga/', importar_csv_maquina, name='importar_csv_maquina'),
    
    path('operador/list', list_operador, name='list_operador'),
    path('operador/add', add_operador, name='add_operador'),
    path('operador/edit/<int:pk>', edit_operador, name='edit_operador'),
    path('api/operadores/', api_operadores, name='api_operadores'),

    # APIS
    path('api/maquinas/', api_maquinas, name='api_maquinas'),
    path('api/setores/', api_setores, name='api_maquinas'),
    path('api/tipo-manutencao/', api_tipo_manutencao, name='api_tipo_manutencao'),
    path('api/status-execucao/', api_status_execucao, name='api_status_execucao')

]
