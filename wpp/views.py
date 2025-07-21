from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.http import HttpResponse
from wpp.utils import OrdemServiceWpp

from datetime import datetime
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

        change = data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {})

        # Verifica se existem atualizações de status
        if 'statuses' in change:
            for status_entry in change['statuses']:
                message_id = status_entry.get('id')
                status_msg = status_entry.get('status')  # sent, delivered, read, failed
                timestamp = status_entry.get('timestamp')
                recipient_id = status_entry.get('recipient_id')  # número do destinatário
                descricao_erro = status_entry.get('errors', [{}])[0].get('title') if 'errors' in status_entry else None

                # Converte timestamp (string em segundos) para datetime
                try:
                    data_status = datetime.fromtimestamp(int(timestamp))
                except Exception as e:
                    print(f"Erro ao converter timestamp: {e}")
                    data_status = None

                # Informa que o número é apenas para mensagens automáticas, e redirecionar para outro whatsapp.
                print(data)

                # Salva ou atualiza no banco
                if message_id and data_status:
                    self.ordem_service.atualizar_status_envio_wa(
                        numero=recipient_id,
                        message_id=message_id,
                        status=status_msg,
                        data_status=data_status,
                        descricao_erro=descricao_erro
                    )
                else:
                    print("❌ Dados incompletos para salvar o status da mensagem.")

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
