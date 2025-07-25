from django.db import models
from django.conf import settings

from cadastro.models import Setor, Maquina, TipoTarefas, Operador

import uuid
import os

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
        ('serralheria','Serralheria'),
        ('fueiro','Fueiro')

    )

    IMPACTO_PRODUCAO_CHOICES = (('alto','Alto'),
                                ('medio','Médio'),
                                ('baixo','Baixo'))

    FERRAMENTAS_CHOICES = (('esmerilhadeira','Esmerilhadeira'),
                           ('tocha','Tocha'))

    AREA_CHOICES = (('predial','Predial'),
                    ('producao','Producao'))

    PRIORIDADE_CHOICES = (('alto','Alto'),
                            ('medio','Médio'),
                            ('baixo','Baixo'))
    
    STATUS_CHOICES = (('aprovar','Aprovar'),('rejeitar','Rejeitar'))

    STATUS_ANDAMENTO_CHOICES = (
                      ('aguardando_atendimento', 'Aguardando atendimento'),
                      ('em_espera','Em espera'),
                      ('em_execucao','Em execuçao'),
                      ('aguardando_material','Aguardando material'),
                      ('finalizada','Finalizada'))
    
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, null=True, blank=True)
    data_abertura = models.DateTimeField(auto_now_add=True, blank=True)
    maq_parada = models.BooleanField(default=False)
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    equipamento_em_falha = models.CharField(max_length=200, choices=EQUIPAMENTO_EM_FALHA_CHOICES, blank=True, null=True)
    setor_maq_solda = models.CharField(max_length=200, choices=SETOR_MAQ_SOLDA_CHOICES, blank=True, null=True)
    impacto_producao = models.CharField(max_length=20, choices=IMPACTO_PRODUCAO_CHOICES, null=True, blank=True)
    tipo_ferramenta = models.CharField(max_length=20, choices=FERRAMENTAS_CHOICES, null=True, blank=True) 
    codigo_ferramenta = models.CharField(max_length=20, null=True, blank=True) 
    video = models.FileField(upload_to='videos/', blank=True, null=True)
    descricao = models.TextField(null=True, blank=True)
    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    planejada = models.BooleanField(default=False)
    prioridade = models.CharField(max_length=20, choices=PRIORIDADE_CHOICES, null=True, blank=True)
    tarefa = models.ForeignKey(TipoTarefas, on_delete=models.CASCADE, null=True, blank=True)
    comentario_manutencao = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True, db_index=True)
    satisfacao_registrada = models.BooleanField(default=False)
    status_andamento = models.CharField(max_length=30, choices=STATUS_ANDAMENTO_CHOICES, default='aguardando_atendimento', db_index=True)
    programacao = models.DateField(null=True, blank=True)
    atribuido = models.ForeignKey(Operador, on_delete=models.CASCADE, related_name='operador_atribuido', null=True, blank=True)
    

    def __str__(self):
        return f'{self.pk} {self.setor} {self.data_abertura} {self.maq_parada}'
    
class Foto(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='fotos')
    imagem = models.ImageField(upload_to='fotos/')

    def save(self, *args, **kwargs):
        # Verifica se a imagem foi fornecida e renomeia com um identificador único
        if self.imagem and not self.pk:  # Garante que a renomeação ocorra apenas na primeira vez que é salva
            extensao = os.path.splitext(self.imagem.name)[1]  # Obtém a extensão do arquivo
            novo_nome = f"{os.path.splitext(self.imagem.name)[0]}_{uuid.uuid4()}{extensao}"
            self.imagem.name = novo_nome  # Define o novo nome da imagem

        super(Foto, self).save(*args, **kwargs)  # Chama o método save() original

    def __str__(self):
        return f'Foto {self.pk} for Solicitacao {self.solicitacao.pk}'
    
