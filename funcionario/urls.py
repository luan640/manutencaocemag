from django.urls import path

from .views import (
    cadastrar_acesso_operador,
    cadastrar_usuario,
    cadastrar_usuarios_csv,
    login_view,
    logout_view,
    primeiro_acesso,
)

urlpatterns = [
    path('', login_view, name='login'),
    path('cadastrar-usuario/', cadastrar_usuario, name='cadastrar_usuario'),
    path('usuarios/operadores/novo/', cadastrar_acesso_operador, name='cadastrar_acesso_operador'),
    path('logout/', logout_view, name='logout'),
    path('cadastrar-usuarios-csv/', cadastrar_usuarios_csv, name='cadastrar_usuarios_csv'),
    path('primeiro-acesso/', primeiro_acesso, name='primeiro_acesso'),
]
