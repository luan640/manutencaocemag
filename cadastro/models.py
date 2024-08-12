from django.db import models

class Setor(models.Model):

    nome = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return self.nome

class Maquina(models.Model):
    
    codigo = models.CharField(max_length=30,unique=True)
    descricao = models.CharField(max_length=100, blank=True, null=True)
    apelido = models.CharField(max_length=100, blank=True, null=True)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='maquina_setor')

    def __str__(self):
        return f'{self.codigo} {self.descricao}'
    
