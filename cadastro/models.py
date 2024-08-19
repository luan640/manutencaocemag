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
    
class MaquinaLocal(models.Model):

    EQUIPAMENTO_EM_FALHA_CHOICES = (
                                ('maquina_de_solda','Máquina de Solda'),
                                ('monovia','Monovia'),
                                ('ferramentas','Ferramentas'),
                                ('robo_kuka','SO-RB-01 - ROBÔ - KUKA'),
                                ('outros','Outros')
                                )

    nome = models.CharField(max_length=200, unique=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    equipamento_em_falha = models.CharField(max_length=200, choices=EQUIPAMENTO_EM_FALHA_CHOICES)

    def __str__(self):
        return f'{self.nome} {self.maquina}'
    
class Operador(models.Model):

    STATUS_CHOICES = (('ativo','Ativo'),
                      ('inativo','Inativo'))

    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=20, unique=True)
    salario = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return self.nome