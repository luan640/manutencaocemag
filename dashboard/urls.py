from django.urls import path
from . import views

urlpatterns = [
    path('ordens-por-mes/<str:area>', views.ordens_por_mes, name='ordens_por_mes'),
    path('setor-mais-solicita/<str:area>', views.setor_mais_solicita, name='setor_mais_solicita'),
    path('horas-servico-por-maquina/<str:area>', views.horas_servico_por_maquina, name='horas_servico_por_maquina'),

    path('dashboard/', views.dashboard_predial, name='dashboard_predial'),
]