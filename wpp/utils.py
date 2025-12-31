import requests
import json
from datetime import datetime

from .models import StatusMensagemWhatsApp

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
        # self.url = "https://graph.facebook.com/v20.0/442779352254085/messages"
        self.url = "https://graph.facebook.com/v20.0/492194993966377/messages"

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
        
        # Verifica se as datas são objetos datetime, se não, faz a conversão
        data_abertura = kwargs.get('data_abertura', 'N/A')
        if isinstance(data_abertura, str):
            data_abertura_dt = datetime.strptime(data_abertura, "%d/%m/%Y")
        else:
            data_abertura_dt = data_abertura

        data_fechamento = kwargs.get('data_fechamento', 'N/A')
        if isinstance(data_fechamento, str):
            data_fechamento_dt = datetime.strptime(data_fechamento, "%d/%m/%Y")
        else:
            data_fechamento_dt = data_fechamento

        # Calculando a diferença em dias
        diferenca = (data_fechamento_dt - data_abertura_dt).days
        dias_em_processo = f"{diferenca} dias"

        maquina = kwargs.get('maquina', 'N/A')
        motivo = kwargs.get('motivo', 'N/A')

        # Formata as datas para envio como texto
        data_abertura_str = data_abertura_dt.strftime("%d/%m/%Y")
        data_fechamento_str = data_fechamento_dt.strftime("%d/%m/%Y")
        
        # Montando o payload para a requisição
        payload = {
            "messaging_product": "whatsapp",
            "to": self.tratar_numero_wa(recipient_number),
            "type": "template",
            "template": {
                "name": "mensagem_satisfacao",  # Nome do template aprovado
                "language": {
                    "code": "pt_BR"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": f"OS{ordem}"},
                            {"type": "text", "text": data_abertura_str},
                            {"type": "text", "text": data_fechamento_str},
                            {"type": "text", "text": dias_em_processo},
                            {"type": "text", "text": maquina},
                            {"type": "text", "text": motivo}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "text",
                                "text": ordem
                            }
                        ]
                    }
                ]
            }
        }

        # Enviando a requisição
        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        print(response.status_code, response.text)
        return response.status_code, response.json()

    def reenviar_mensagem_finalizar_ordem(self, recipient_number, kwargs):
        # Extraindo os valores de kwargs
        ordem = kwargs.get('ordem', 'N/A')
        
        # Verifica se as datas são objetos datetime, se não, faz a conversão
        data_abertura = kwargs.get('data_abertura', 'N/A')
        if isinstance(data_abertura, str):
            data_abertura_dt = datetime.strptime(data_abertura, "%d/%m/%Y")
        else:
            data_abertura_dt = data_abertura

        data_fechamento = kwargs.get('data_fechamento', 'N/A')
        if isinstance(data_fechamento, str):
            data_fechamento_dt = datetime.strptime(data_fechamento, "%d/%m/%Y")
        else:
            data_fechamento_dt = data_fechamento

        # Calculando a diferença em dias
        diferenca = (data_fechamento_dt - data_abertura_dt).days
        dias_em_processo = f"{diferenca} dias"

        maquina = kwargs.get('maquina', 'N/A')
        motivo = kwargs.get('motivo', 'N/A')

        # Formata as datas para envio como texto
        data_abertura_str = data_abertura_dt.strftime("%d/%m/%Y")
        data_fechamento_str = data_fechamento_dt.strftime("%d/%m/%Y")
        
        # Montando o payload para a requisição
        payload = {
            "messaging_product": "whatsapp",
            "to": self.tratar_numero_wa(recipient_number),
            "type": "template",
            "template": {
                "name": "reenviar_confirmacao_os",  # Nome do template aprovado
                "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": f"OS{ordem}"},
                            {"type": "text", "text": data_abertura_str},
                            {"type": "text", "text": data_fechamento_str},
                            {"type": "text", "text": dias_em_processo},
                            {"type": "text", "text": maquina},
                            {"type": "text", "text": motivo}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "text",
                                "text": ordem
                            }
                        ]
                    }
                ]
            }
        }

        # Enviando a requisição
        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        return response.status_code, response.json()

    def mensagem_atribuir_ordem(self, recipient_number, kwargs):
        # Extraindo os valores de kwargs
        ordem = str(kwargs.get('ordem', 'N/A'))
        maquina = str(kwargs.get('maquina', 'N/A'))
        motivo = str(kwargs.get('motivo', 'N/A'))
        solicitante = str(kwargs.get('solicitante', 'N/A'))
        prioridade = str(kwargs.get('prioridade', 'N/A'))  # Corrigido

        print(ordem, maquina, motivo, solicitante, prioridade, recipient_number)

        # Montando o payload para a requisição
        payload = {
            "messaging_product": "whatsapp",
            "to": self.tratar_numero_wa(recipient_number),
            "type": "template",
            "template": {
                "name": "purchase_transaction_alert",  # Nome do template aprovado
                "language": {
                    "code": "pt_BR"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": ordem},
                            {"type": "text", "text": solicitante},
                            {"type": "text", "text": maquina},
                            {"type": "text", "text": motivo},
                            {"type": "text", "text": prioridade},
                        ]
                    },
                ]
            }
        }

        # Enviando a requisição
        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        print(response.status_code, response.text)  # Logar a resposta completa

        return response.status_code, response.json()

    def mensagem_ordem_rejeitada_predial(self, recipient_number, kwargs):
        ordem = str(kwargs.get('ordem', 'N/A'))
        solicitante = str(kwargs.get('solicitante', 'N/A'))
        data_abertura = kwargs.get('data_abertura', 'N/A')
        local_maquina = str(kwargs.get('local_maquina', 'N/A'))
        motivo = str(kwargs.get('motivo', 'N/A'))
        motivo_cancelamento = str(kwargs.get('motivo_cancelamento', 'N/A'))

        if isinstance(data_abertura, str):
            data_abertura_str = data_abertura
        else:
            data_abertura_str = data_abertura.strftime("%d/%m/%Y")

        payload = {
            "messaging_product": "whatsapp",
            "to": self.tratar_numero_wa(recipient_number),
            "type": "template",
            "template": {
                "name": "ordem_rejeitada_predial",
                "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": f"*{solicitante}*"},
                            {"type": "text", "text": f"#OS{ordem}"},
                            {"type": "text", "text": data_abertura_str},
                            {"type": "text", "text": local_maquina},
                            {"type": "text", "text": motivo},
                            {"type": "text", "text": motivo_cancelamento},
                        ]
                    },
                ]
            }
        }

        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        print(response.status_code, response.text)
        return response.status_code, response.json()

    def sucesso_criar_conta(self, number_cadastrado, kwargs):
        # Extraindo os valores de kwargs
        login = str(kwargs.get('login', 'N/A'))
        password = str(kwargs.get('password', 'N/A'))

        # Montando o payload para a requisição
        payload = {
            "messaging_product": "whatsapp",
            "to": number_cadastrado,
            "type": "template",
            "template": {
                "name": "sucesso_criar_acesso",  # Nome do template aprovado
                "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": login},
                            {"type": "text", "text": password},
                        ]
                    },
                ]
            }
        }

        # Enviando a requisição
        response = requests.post(self.url, headers=self.headers, data=json.dumps(payload))
        print(response.status_code, response.text)  # Logar a resposta completa

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
    
    def responder_automaticamente(self, wa_id, phone_number_id):
        url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
        headers = {
            "Authorization": "Bearer EAAwIFMrHx4cBOZBCakd7M5mav5ZBAJfUFZB2y8bTakplZBeKXPiFkRLQkA40ZCqstZASwTGbzywAVOZABRgV3GN2MW4klZBnqwnlU8LluSktpEV7yM2lRPJMiNt2WCOh5jyTOHhI5COFVwiafVh2TmqAVOJQJrtkPbMb00qAo3G28kRAtYSbupo3aZCCri4oinkD7kAZDZD",  # Token de acesso fornecido na inicialização
            "Content-Type": "application/json"
        }

        mensagem = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {
                "body": (
                    "*Olá!* 👋\n\n"
                    "Esse número é usado apenas para *mensagens automáticas*.\n"
                    "Se quiser conversar com o setor *RH*, clique no botão abaixo:\n\n"
                    "📞 *RH*: https://wa.me/5585998330227\n\n"
                    "_Agradecemos o seu contato!_ 💛"
                )
            }
        }

        response = requests.post(url, headers=headers, json=mensagem)
        print(f"✅ Resposta automática enviada para {wa_id}. Status: {response.status_code}")

    def atualizar_status_envio_wa(self, numero, message_id, status, data_status, descricao_erro=None):
        """
        Atualiza ou cria o status da mensagem do WhatsApp com base no message_id.
        
        :param numero: Número do destinatário (wa_id)
        :param message_id: ID único da mensagem enviada
        :param status: Status recebido (sent, delivered, read, failed, etc)
        :param data_status: datetime da mudança de status
        :param descricao_erro: (opcional) mensagem de erro caso haja falha
        """
        StatusMensagemWhatsApp.objects.update_or_create(
            message_id=message_id,
            defaults={
                "telefone": numero,
                "status": status,
                "data_status": data_status,
                "descricao_erro": descricao_erro
            }
        )
