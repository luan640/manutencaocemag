from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.http import HttpResponse
from wpp.utils import tratar_numero_wa, OrdemServiceWpp

import requests

class WhatsAppWebhookView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ordem_service = OrdemServiceWpp()

    def get(self, request, *args, **kwargs):
        VERIFY_TOKEN = 'meu_token_seguro'
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        if mode and token == VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        else:
            return HttpResponse('Erro de verificação', status=403)

    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)

        if 'contacts' in data['entry'][0]['changes'][0]['value']:
            recipient_number = data['entry'][0]['changes'][0]['value']['contacts'][0]['wa_id']
            recipient_number_tratado = self.ordem_service.tratar_numero_wa(recipient_number)

            # Verifique se a mensagem contém uma resposta interativa
            if 'messages' in data['entry'][0]['changes'][0]['value']:
                message = data['entry'][0]['changes'][0]['value']['messages'][0]

                # Se for uma resposta interativa
                if message['type'] == 'interactive' and 'button' in message['interactive']:
                    resposta = message['interactive']['button']['reply']['title']
                    self.ordem_service.processar_resposta(recipient_number_tratado, resposta)
                else:
                    # Caso a mensagem não seja interativa, pode ser tratada de outra forma
                    print(f"Mensagem não interativa recebida: {message}")

        return Response(status=status.HTTP_200_OK)

class AccountView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        cc = data.get('cc')
        phone_number = data.get('phone_number')
        method = data.get('method')
        cert = data.get('cert')
        pin = data.get('pin')

        if not all([cc, phone_number, method, cert]):
            return Response({"error": "Campos obrigatórios ausentes."}, status=status.HTTP_400_BAD_REQUEST)

        # Endpoint do cliente oficial da Meta (ou seu container rodando a API oficial)
        whatsapp_api_url = "http://localhost:8080/v1/account"

        payload = {
            "cc": cc,
            "phone_number": phone_number,
            "method": method,
            "cert": cert,
        }

        if pin:
            payload["pin"] = pin

        try:
            response = requests.post(whatsapp_api_url, json=payload, timeout=10, verify=False)
            response.raise_for_status()
            return Response(response.json(), status=response.status_code)
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Erro ao se comunicar com API do WhatsApp", "details": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
