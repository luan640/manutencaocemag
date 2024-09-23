from django.urls import path
from . import views
from .views import historico_execucao, execucao_data

urlpatterns = [
    path('historico/', historico_execucao, name='historico_execucao'),
    path('historico/processa-historico/', execucao_data, name='execucao_data'),

]