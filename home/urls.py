from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('producao/', views.home_producao, name='home_producao'),
    path('predial/', views.home_predial, name='home_predial'),
    path('solicitante/', views.home_solicitante, name='home_solicitante'),
    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)