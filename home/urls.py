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



] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)