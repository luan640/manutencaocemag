import requests
import json

# openai.api_key = aqui seu token

def tratar_numero_wa(wa_id):
    # Verifique se o número começa com o código de país +55 (Brasil)
    if wa_id.startswith("55") and len(wa_id) >= 12:  # Considerar números com 12 ou mais dígitos
        # Verificar se já tem o dígito 9
        codigo_area = wa_id[4:6]  # Extrai o código de área
        numero_restante = wa_id[6:]
        
        if not numero_restante.startswith('9'):
            # Inserir o dígito 9 após o código de área
            return wa_id[:4] + '9' + wa_id[4:]
        else:
            return wa_id  # Se já tiver o dígito 9, retorna o número sem modificação
    else:
        # Se não for um número no formato esperado, retorna o número sem modificação
        return wa_id
    
class OrdemServiceWpp:
    def __init__(self):
        self.url = "https://graph.facebook.com/v20.0/105626809259314/messages"
        self.headers = {
            "Authorization": "Bearer EAAwIFMrHx4cBOZBCakd7M5mav5ZBAJfUFZB2y8bTakplZBeKXPiFkRLQkA40ZCqstZASwTGbzywAVOZABRgV3GN2MW4klZBnqwnlU8LluSktpEV7yM2lRPJMiNt2WCOh5jyTOHhI5COFVwiafVh2TmqAVOJQJrtkPbMb00qAo3G28kRAtYSbupo3aZCCri4oinkD7kAZDZD",  # Token de acesso fornecido na inicialização
            "Content-Type": "application/json"
        }
        self.user_states = {}  # Armazena o estado do fluxo para cada usuário

    def tratar_numero_wa(self, numero):
        if not numero.startswith('55'):
            return f'55{numero}'
        return numero

    def mensagem_finalizar_ordem(self, recipient_number, kwargs):
        # Extraindo os valores de kwargs
        ordem = kwargs.get('ordem', 'N/A')
        data_abertura = kwargs.get('data_abertura', 'N/A')
        data_fechamento = kwargs.get('data_fechamento', 'N/A')
        maquina = kwargs.get('maquina', 'N/A')
        descricao = kwargs.get('descricao', 'N/A')
        motivo = kwargs.get('motivo', 'N/A')
        link = kwargs.get('link', 'N/A')

        # Criando a mensagem
        mensagem = f"""Olá, a ordem de serviço #{ordem} foi finalizada.

*Data de abertura*: {data_abertura}
*Data de fechamento*: {data_fechamento}
*Máquina*: {maquina} - {descricao}
*Motivo*: {motivo}

Para confirmar a satisfação com o serviço, acesse o link: {link}

"""

        # Montando o payload para a requisição
        payload = {
            "messaging_product": "whatsapp",
            "to": self.tratar_numero_wa(recipient_number),
            "type": "text",
            "text": {
                "body": mensagem
            }
        }

        # Enviando a requisição
        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        return response.status_code, response.json()


    def enviar_mensagem(self, mensagem):
        # Envia a mensagem para a API do WhatsApp
        try:
            response = requests.post(self.url, headers=self.headers, data=json.dumps(mensagem))
            if response.status_code == 200:
                return response.status_code, response.json()
            else:
                return response.status_code, response.text
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            return None, str(e)
