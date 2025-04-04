from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),

    path('mtbf-maquina/', views.mtbf_maquina, name='mtbf_maquina'),
    path('mttr-maquina/', views.mttr_maquina, name='mttr_maquina'),
    path('disponibilidade-maquina/', views.disponibilidade_maquina, name='disponibilidade_maquina'),
    path('ordens-prazo/', views.ordens_prazo, name='ordens_prazo'),
    path('relacao-tipo-ordem/', views.relacao_por_tipo_ordem, name='relacao_por_tipo_ordem'),
    path('tempo-maquina-parada/', views.maquina_parada, name='maquina_parada'),
    path('solicitacao-por-setor/', views.solicitacao_setor, name='solicitacao_setor'),

    path('exportar-maquina-parada/', views.exportar_maquina_parada_excel, name='exportar_maquina_parada_excel'),
    path('exportar-solicitacao-setor/', views.exportar_solicitacao_setor, name='exportar_solicitacao_setor'),
    path('exportar-mtbf-maquina/', views.exportar_mtbf_maquina, name='exportar_mtbf_maquina'),
    path('exportar-mttr-maquina/', views.exportar_mttr_maquina, name='exportar_mttr_maquina'),
    path('exportar-disponibilidade-maquina/', views.exportar_disponibilidade_maquina, name='exportar_disponibilidade_maquina'),
    path('exportar-horas-trabalhadas-setor/', views.exportar_horas_trabalhadas_setor, name='exportar_horas_trabalhadas_setor'),
    path('exportar-horas-trabalhadas-tipo/', views.exportar_horas_trabalhadas_tipo, name='exportar_horas_trabalhadas_tipo'),

    path('ordens-abertas/', views.quantidade_abertura_ordens, name='quantidade_abertura_ordens'),
    path('ordens-finalizada/', views.quantidade_finalizada, name='quantidade_finalizada'),
    path('ordens-aguardando-material/', views.quantidade_aguardando_material, name='quantidade_aguardando_material'),
    path('ordens-em-aberto-atrasadas/', views.quantidade_atrasada_view, name='quantidade_atrasada_view'),
    path('ordens-em-execucao/', views.quantidade_em_execucao, name='quantidade_em_execucao'),
    path('tempo-medio-finalizacao/', views.tempo_medio_finalizar, name='tempo_medio_finalizar'),
    path('tempo-medio-abertura/', views.tempo_medio_abertura, name='tempo_medio_abertura'),
    path('horas-trabalhadas-setor/', views.horas_trabalhadas_setor, name='horas_trabalhadas_setor'),
    path('horas-trabalhadas-tipo/', views.horas_trabalhadas_tipo, name='horas_trabalhadas_tipo'),
    path('disponibilidade-geral/', views.disponibilidade_geral, name='disponibilidade_geral'),

]