from django.db import models

from cadastro.models import Setor, Maquina

class Solicitacao(models.Model):
    
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    data_abertura = models.DateTimeField()#auto_now_add=True, blank=True)
    maq_parada = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.pk} {self.setor} {self.data_abertura} {self.maq_parada}'
