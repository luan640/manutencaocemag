from django.db import models

from cadastro.models import Maquina, Operador, TipoTarefas
from solicitacao.models import Solicitacao

class PlanoPreventiva(models.Model):
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, related_name='planos_preventiva')
    nome = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    periodicidade = models.IntegerField(help_text="Número de dias entre cada execução")
    abertura_automatica = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.maquina} {self.nome}'

class TarefaPreventiva(models.Model):

    RESPONSABILIDADE_CHOICE = (('eletrica','Elétrica'),
                                ('mecanica','Mecânica'),
                                ('predial','Predial'))

    plano = models.ForeignKey(PlanoPreventiva, on_delete=models.CASCADE, related_name='tarefas_preventiva')
    descricao = models.TextField()
    responsabilidade = models.CharField(max_length=20, choices=RESPONSABILIDADE_CHOICE)

    def __str__(self):
        return f'{self.plano} {self.descricao}'

class SolicitacaoPreventiva(models.Model):

    ordem = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='preventiva_solicitacao')
    plano = models.ForeignKey(PlanoPreventiva, on_delete=models.CASCADE, related_name='execucao_plano')
    finalizada = models.BooleanField(default=False)
    data = models.DateField()

    def __str__(self):
        return f'{self.plano} {self.data}'
