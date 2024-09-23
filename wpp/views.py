from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'POST':
        # Captura os dados do POST request
        try:
            payload = json.loads(request.body)
            print("Webhook received:", payload)
            
            # Processamento dos dados do webhook
            if 'messages' in payload:
                for message in payload['messages']:
                    from_number = message['from']
                    text = message.get('text', {}).get('body', '')
                    print(f"Mensagem de {from_number}: {text}")
                    
                    # Exemplo: lógica para responder ou processar a mensagem
                    # Você pode adicionar sua lógica aqui, como enviar uma resposta automática
                    # ou atualizar uma base de dados.

            return JsonResponse({'status': 'Message received'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    elif request.method == 'GET':
        # Verificação do Webhook para configuração inicial
        verify_token = request.GET.get('hub.verify_token')
        if verify_token == settings.YOUR_VERIFY_TOKEN:
            return HttpResponse(request.GET.get('hub.challenge'))
        else:
            return HttpResponse('Invalid verification token', status=403)
    
    return HttpResponse('Invalid request method', status=405)
