from django.core.management.base import BaseCommand
from preventiva.crons import verificar_abertura_solicitacoes_preventivas

class Command(BaseCommand):
    help = 'Cron para abertura de preventivas'

    def handle(self, *args, **kwargs):
        verificar_abertura_solicitacoes_preventivas()
