from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status

from wpp.utils import tratar_numero_wa, OrdemServiceWpp

# class WhatsAppWebhookView(APIView):

#     def get(self, request, *args, **kwargs):
#         VERIFY_TOKEN = 'meu_token_seguro'
#         mode = request.query_params.get('hub.mode')
#         token = request.query_params.get('hub.verify_token')
#         challenge = request.query_params.get('hub.challenge')

#         if mode and token == VERIFY_TOKEN:
#             return HttpResponse(challenge, status=200)
#         else:
#             return HttpResponse('Erro de verificação', status=403)

#     def post(self, request, *args, **kwargs):
#         data = request.data
#         print('Mensagem recebida:', data)

#         # Verifique se a chave "contacts" está presente
#         if 'contacts' in data['entry'][0]['changes'][0]['value']:
#             # Extraia o wa_id da mensagem recebida
#             recipient_number = data['entry'][0]['changes'][0]['value']['contacts'][0]['wa_id']
#             recipient_number_tratado = tratar_numero_wa(recipient_number)  # Tratamento do número
#             print(f"WA ID tratado: {recipient_number_tratado}")

#             received_message = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']

#             # Gere uma resposta do ChatGPT para a mensagem recebida
#             # response_message = get_chatgpt_response(received_message)

#             # Envie a resposta de volta via API do WhatsApp
#             # status_code, response_data = send_whatsapp_message(recipient_number_tratado)#, response_message)
#             # print(f"Status: {status_code}, Response: {response_data}")

#         # Verifique se a chave "statuses" está presente
#         elif 'statuses' in data['entry'][0]['changes'][0]['value']:
#             # Trata as atualizações de status, como "delivered", "read", etc.
#             status_update = data['entry'][0]['changes'][0]['value']['statuses'][0]
#             print(f"Status update: {status_update}")

#         return Response(status=status.HTTP_200_OK)

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
        print('Mensagem recebida:', data)

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