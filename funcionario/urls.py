from django.urls import path
from .views import login_view, cadastrar_usuario, logout_view, cadastrar_usuarios_csv,primeiro_acesso

urlpatterns = [
    path('', login_view, name='login'),
    # path('logout/', logout_view, name='logout'),
    path('cadastrar-usuario/', cadastrar_usuario, name='cadastrar_usuario'),
    path('logout/', logout_view, name='logout'),
    path('cadastrar-usuarios-csv/', cadastrar_usuarios_csv, name='cadastrar_usuarios_csv'),
    path('primeiro-acesso/', primeiro_acesso, name='primeiro_acesso'),

]