from django.db import models

from solicitacao.models import Solicitacao
from cadastro.models import Operador

class InfoSolicitacao(models.Model):
    
    TIPO_CHOICES = (('corretiva','Corretiva'),
                    ('preditiva','Preditiva'),
                    ('preventiva',' Preventiva'),
                    ('preventiva_programada',' Preventiva programada'),
                    ('apoio','Apoio'),
                    ('projetos','Projetos'),
                    ('sesmt','SESMT'),
                    ('corretiva_programada','Corretiva programada'))

    AREA_CHOICES = (('predial','Predial'),
                    ('mecanica','Mecânica'),
                    ('eletrica','Elétrica'))

    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='info_solicitacao')
    tipo_manutencao = models.CharField(max_length=40, choices=TIPO_CHOICES)
    area_manutencao = models.CharField(max_length=20, choices=AREA_CHOICES)

    def __str__(self):
        return self.tipo_manutencao

class Execucao(models.Model):

    STATUS_CHOICES = (
                      ('aguardando_atendimento', 'Aguardando atendimento'),
                      ('em_espera','Em espera'),
                      ('em_execucao','Em execuçao'),
                      ('aguardando_material','Aguardando material'),
                      ('finalizada','Finalizada'))

    n_execucao = models.IntegerField(blank=True, null=True)
    ordem = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='execucao_solicitacao')
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    observacao = models.TextField(blank=True, null=True)
    operador = models.ManyToManyField(Operador, blank=True)
    che_maq_parada = models.BooleanField(default=False)
    exec_maq_parada = models.BooleanField(default=False)
    apos_exec_maq_parada = models.BooleanField(default=False)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='em_espera')
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ordem', 'n_execucao')

    def save(self, *args, **kwargs):
        creating = not self.pk  # Verifica se é uma nova instância (não está sendo atualizada)
        
        if creating:
            max_n_execucao = Execucao.objects.filter(ordem=self.ordem).aggregate(models.Max('n_execucao'))['n_execucao__max']
            self.n_execucao = max_n_execucao + 1 if max_n_execucao is not None else 0

        super().save(*args, **kwargs)

        # Se a execução é nova (número de execução é 1) ou se há uma condição para atualizar MaquinaParada
        if creating:
            if self.n_execucao == 0:
                if self.apos_exec_maq_parada:
                    data_inicio = self.ordem.data_abertura if self.che_maq_parada else self.data_inicio
                    MaquinaParada.objects.get_or_create(
                        ordem=self.ordem,
                        execucao=self,
                        defaults={'data_inicio': data_inicio, 'data_fim': None}
                    )
                elif self.che_maq_parada:
                    MaquinaParada.objects.get_or_create(
                        ordem=self.ordem,
                        execucao=self,
                        defaults={'data_inicio': self.ordem.data_abertura, 'data_fim': self.data_fim}
                    )
                elif self.exec_maq_parada:
                    MaquinaParada.objects.get_or_create(
                        ordem=self.ordem,
                        execucao=self,
                        defaults={'data_inicio': self.data_inicio, 'data_fim': self.data_fim}
                    )
            else:
                # Atualizar ou criar nova entrada para execuções subsequentes
                execucao_anterior = Execucao.objects.filter(ordem=self.ordem, n_execucao=self.n_execucao - 1).first()
                
                if execucao_anterior:
                    maquina_parada_anterior = MaquinaParada.objects.filter(execucao=execucao_anterior).first()
                    if maquina_parada_anterior and not maquina_parada_anterior.data_fim:
                        maquina_parada_anterior.data_fim = self.data_inicio
                        maquina_parada_anterior.save()

                if self.apos_exec_maq_parada:
                    MaquinaParada.objects.get_or_create(
                        ordem=self.ordem,
                        execucao=self,
                        defaults={'data_inicio': self.data_inicio, 'data_fim': None}
                    )
                elif self.exec_maq_parada:
                    MaquinaParada.objects.get_or_create(
                        ordem=self.ordem,
                        execucao=self,
                        defaults={'data_inicio': self.data_inicio, 'data_fim': self.data_fim}
                    )

    def duracao_servico(self):
        """Calcula a duração da execução em horas"""
        if self.data_fim and self.data_inicio:
            duracao = self.data_fim - self.data_inicio
            return duracao.total_seconds() / 3600  # Converte segundos para horas
        return 0  # Retorna 0 se a execução ainda não foi finalizada
    
class MaquinaParada(models.Model):
    ordem = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='ordem_maquinaparada')
    execucao = models.ForeignKey(Execucao, on_delete=models.CASCADE, related_name='maquina_parada', null=True, blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.data_inicio} - {self.data_fim if self.data_fim else "em andamento"}'


