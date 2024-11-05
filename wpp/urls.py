from django.urls import path
from .views import WhatsAppWebhookView,AccountView

urlpatterns = [
    path('webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    path('v1/account', AccountView.as_view(), name='account_view'),  # Rota para o POST

]
