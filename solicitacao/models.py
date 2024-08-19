from django.db import models
from django.contrib.auth.models import User

from cadastro.models import Setor, Maquina, MaquinaLocal

class Solicitacao(models.Model):
    
    EQUIPAMENTO_EM_FALHA_CHOICES = (('maquina_de_solda','Máquina de Solda'),
                                    ('monovia','Monovia'),
                                    ('ferramentas','Ferramentas'),
                                    ('robo_kuka','SO-RB-01 - ROBÔ - KUKA'),
                                    ('outros','Outros')
                                    )
    
    SETOR_MAQ_SOLDA_CHOICES = (
        ('laterais','Laterais'),
        ('eixos','Eixos'),
        ('icamentos','Içamentos'),
        ('plataforma','Plataforma'),
        ('chassi','Chassi'),
        ('tanque','Tanque'),
        ('cacamba','Caçamba'),
        ('serralheria','Serralheria')
    )

    IMPACTO_PRODUCAO_CHOICES = (('alto','Alto'),
                                ('medio','Médio'),
                                ('baixo','Baixo'))

    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE)
    data_abertura = models.DateTimeField(auto_now_add=True, blank=True)
    maq_parada = models.BooleanField(default=False)
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE)    
    equipamento_em_falha = models.CharField(max_length=200, choices=EQUIPAMENTO_EM_FALHA_CHOICES) # se setor = solda
    maquina_local = models.ForeignKey(MaquinaLocal, on_delete=models.CASCADE) # se setor = solda
    setor_maq_solda = models.CharField(max_length=200, choices=SETOR_MAQ_SOLDA_CHOICES) # se setor = solda
    impacto_producao = models.CharField(max_length=20, choices=IMPACTO_PRODUCAO_CHOICES)
    video = models.FileField(upload_to='videos/', blank=True, null=True)

    def __str__(self):
        return f'{self.pk} {self.setor} {self.data_abertura} {self.maq_parada}'

class Foto(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='fotos')
    imagem = models.ImageField(upload_to='fotos/')

    def __str__(self):
        return f'Foto {self.pk} for Solicitacao {self.solicitacao.pk}'
