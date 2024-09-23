from django.urls import path
from .views import login_view, logout_view, cadastrar_usuario #, home_redirect

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('cadastrar-usuario/', cadastrar_usuario, name='cadastrar_usuario'),

]