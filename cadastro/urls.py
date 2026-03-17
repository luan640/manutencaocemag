from django.urls import path
from .views import *
from . import checklist_views

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
    path('api/maquinas-list/', api_maquinas_list, name='api_maquinas_list'),
    path('api/setores/', api_setores, name='api_maquinas'),
    path('api/tipo-manutencao/', api_tipo_manutencao, name='api_tipo_manutencao'),
    path('api/status-execucao/', api_status_execucao, name='api_status_execucao'),
    path('api/tarefa-rotina/', api_tarefa_rotina, name='api_tarefa_rotina'),

    # Checklists de manutencao autonoma
    path('checklists/', checklist_views.checklists_manage_view, name='checklists_manage_view'),
    path('checklists/historico/', checklist_views.checklists_history_view, name='checklists_history_view'),
    path('checklists/calendario/', checklist_views.checklists_calendar_view, name='checklists_calendar_view'),
    path('checklists/api/forms/', checklist_views.api_checklist_forms, name='api_checklist_forms'),
    path('checklists/api/calendar/', checklist_views.api_checklist_calendar, name='api_checklist_calendar'),
    path('checklists/api/reset/', checklist_views.api_checklist_reset, name='api_checklist_reset'),
    path('checklists/api/forms/<int:form_id>/', checklist_views.api_checklist_form_detail, name='api_checklist_form_detail'),
    path('checklists/api/forms/<int:form_id>/versions/', checklist_views.api_checklist_form_versions, name='api_checklist_form_versions'),
    path('checklists/<int:form_id>/qrcode/', checklist_views.checklist_qrcode_view, name='checklist_qrcode_view'),
    path('checklists/api/responses/', checklist_views.api_checklist_responses, name='api_checklist_responses'),
    path('checklists/api/responses/<int:response_id>/', checklist_views.api_checklist_response_detail, name='api_checklist_response_detail'),
    path('checklists/respostas/<int:response_id>/pdf/', checklist_views.checklist_response_pdf, name='checklist_response_pdf'),
    path('checklists/public/<uuid:token>/', checklist_views.checklist_public_view, name='checklist_public_view'),
    path('checklists/api/public/<uuid:token>/', checklist_views.api_checklist_public_form, name='api_checklist_public_form'),
    path('checklists/api/public/<uuid:token>/funcionarios/', checklist_views.api_checklist_public_funcionarios, name='api_checklist_public_funcionarios'),
    path('checklists/api/public/<uuid:token>/submit/', checklist_views.api_checklist_public_submit, name='api_checklist_public_submit'),

]
