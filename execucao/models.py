from django.db import models

from solicitacao.models import Solicitacao

class Execucao(models.Model):
    n_execucao = models.IntegerField(blank=True, null=True)
    ordem = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='execucao_solicitacao')
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    che_maq_parada = models.BooleanField(default=False)
    exec_maq_parada = models.BooleanField(default=False)
    apos_exec_maq_parada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('ordem', 'n_execucao')

    def save(self, *args, **kwargs):
        if not self.pk:  # Verifica se é uma nova instância (não está sendo atualizada)
            max_n_execucao = Execucao.objects.filter(ordem=self.ordem).aggregate(models.Max('n_execucao'))['n_execucao__max']
            self.n_execucao = max_n_execucao + 1 if max_n_execucao is not None else 1

        super().save(*args, **kwargs)

        if self.n_execucao == 1:
            # Primeira execução
            if self.apos_exec_maq_parada and not self.che_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.ordem.data_abertura,
                    data_fim=None
                )
            elif self.apos_exec_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.data_inicio,
                    data_fim=None
                )
            elif self.che_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.ordem.data_abertura,
                    data_fim=self.data_fim
                )
            elif self.exec_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.data_inicio,
                    data_fim=self.data_fim
                )
        else:
            # Não é a primeira execução
            execucao_anterior = Execucao.objects.filter(ordem=self.ordem, n_execucao=self.n_execucao-1).first()
            maquina_parada_anterior = MaquinaParada.objects.filter(execucao=execucao_anterior)

            if execucao_anterior:
                maquina_parada_anterior = MaquinaParada.objects.filter(execucao=execucao_anterior).first()

                if maquina_parada_anterior and not maquina_parada_anterior.data_fim:
                    maquina_parada_anterior.data_fim = self.data_inicio
                    maquina_parada_anterior.save()
            
            if self.apos_exec_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.data_inicio,
                    data_fim=self.data_fim
                )
            elif self.che_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=execucao_anterior.data_fim,
                    data_fim=self.data_fim
                )
            elif self.exec_maq_parada:
                MaquinaParada.objects.create(
                    ordem=self.ordem,
                    execucao=self,
                    data_inicio=self.data_inicio,
                    data_fim=self.data_fim
                )

class MaquinaParada(models.Model):
    ordem = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='ordem_maquinaparada')
    execucao = models.ForeignKey(Execucao, on_delete=models.CASCADE, related_name='maquina_parada', null=True, blank=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.data_inicio} - {self.data_fim if self.data_fim else "em andamento"}'

