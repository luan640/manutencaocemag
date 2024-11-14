from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('producao/', views.home_producao, name='home_producao'),
    path('predial/', views.home_predial, name='home_predial'),
    path('solicitante/', views.home_solicitante, name='home_solicitante'),
    
    path('producao/solicitacoes/', views.solicitacoes_producao, name='solicitacoes_producao'),
    path('producao/aguardando-primeiro-atendimento/', views.aguardando_primeiro_atendimento_producao, name='aguardando_primeiro_atendimento_producao'),
    path('producao/maquinas-paradas/', views.maquinas_paradas_producao, name='maquinas_paradas_producao'),

    path('predial/solicitacoes/', views.solicitacoes_predial, name='solicitacoes_predial'),
    path('predial/aguardando-primeiro-atendimento/', views.aguardando_primeiro_atendimento_predial, name='aguardando_primeiro_atendimento_predial'),

    path('reenviar-mensagem/<int:ordem_id>/', views.reenviar_mensagem, name='reenviar_mensagem'),

    path('historico/<int:pk>/', views.historico_ordem, name='historico_ordem'),
    path('mais-detalhes/<int:pk>/', views.mais_detalhes_ordem, name='mais_detalhes_ordem'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)