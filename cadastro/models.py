import uuid
from datetime import date

from django.db import models

class Setor(models.Model):

    nome = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return self.nome

class Maquina(models.Model):
    
    AREA_CHOICES = (('predial','Predial'),
                    ('producao','Produção'))

    CRITICIDADE_CHOICES = (('a','A'),
                           ('b','B'),
                           ('c','C'))

    TIPO_CHOICES = (('monovia','Monovia'),('maquina_de_solda','Máquina de Solda'),('robo_kuka','ROBÔ KUKA'),('outros','Outros'))

    codigo = models.CharField(max_length=30)
    descricao = models.CharField(max_length=100, blank=True, null=True)
    apelido = models.CharField(max_length=100, blank=True, null=True)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='maquina_setor')
    tombamento = models.CharField(max_length=40, blank=True, null=True)
    area = models.CharField(max_length=20,choices=AREA_CHOICES)
    criticidade = models.CharField(max_length=2, choices=CRITICIDADE_CHOICES)
    foto = models.ImageField(upload_to='fotos/', null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, blank=True, null=True)
    maquina_critica = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['codigo', 'setor', 'area'], name='unique_maquina')
        ]

    def __str__(self):
        return f'{self.codigo} {self.descricao}'

class Operador(models.Model):

    STATUS_CHOICES = (('ativo','Ativo'),
                      ('inativo','Inativo'))

    AREA_CHOICES = (('predial','Predial'),
                    ('producao','Produção'))

    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=20, unique=True)
    salario = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    telefone = models.CharField(max_length=13, blank=True, null=True)

    def __str__(self):
        return self.nome
    
    def save(self, *args, **kwargs):
        # Adicionar "55" ao telefone, se necessário
        if self.telefone and not self.telefone.startswith('55'):
            self.telefone = '55' + self.telefone

        super(Operador, self).save(*args, **kwargs)
    
class TipoTarefas(models.Model):

    nome = models.CharField(max_length=100, unique=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.nome
    
class PecaUtilizada(models.Model):

    codigo = models.CharField(max_length=10, unique=True)
    descricao = models.CharField(max_length=255),
    valor = models.FloatField(default=0)

    def __str__(self):
        return self.descricao
    
class Checklist(models.Model):

    nome = models.CharField(max_length=100)
    maquinas = models.ManyToManyField(Maquina, related_name='checklists')  # Relacionamento ManyToMany

class ItensCheckList(models.Model):

    nome = models.CharField(max_length=100)
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='itens')


class ChecklistFormulario(models.Model):
    titulo = models.CharField(max_length=160)
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name='checklist_formularios',
    )
    criado_por = models.ForeignKey(
        'funcionario.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklists_formulario_criados',
    )
    ativo = models.BooleanField(default=True)
    token_publico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    versao_atual = models.ForeignKey(
        'ChecklistFormularioVersao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ('-atualizado_em',)

    def __str__(self):
        return f'{self.titulo} - {self.maquina.codigo}'


class ChecklistFormularioVersao(models.Model):
    formulario = models.ForeignKey(
        ChecklistFormulario,
        on_delete=models.CASCADE,
        related_name='versoes',
    )
    numero = models.PositiveIntegerField()
    titulo = models.CharField(max_length=160)
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name='checklist_versoes',
    )
    criado_por = models.ForeignKey(
        'funcionario.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklists_versao_criados',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('formulario', 'numero')
        ordering = ('-numero',)

    def __str__(self):
        return f'{self.formulario_id} v{self.numero}'


class ChecklistPergunta(models.Model):
    TIPO_INPUT = 'input'
    TIPO_ESCOLHA_UNICA = 'single_choice'
    TIPO_MULTIPLA_ESCOLHA = 'multiple_choice'

    TIPO_CHOICES = (
        (TIPO_INPUT, 'Input'),
        (TIPO_ESCOLHA_UNICA, 'Escolha unica'),
        (TIPO_MULTIPLA_ESCOLHA, 'Multipla escolha'),
    )

    versao = models.ForeignKey(
        ChecklistFormularioVersao,
        on_delete=models.CASCADE,
        related_name='perguntas',
    )
    ordem = models.PositiveIntegerField(default=1)
    texto = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    obrigatoria = models.BooleanField(default=True)

    class Meta:
        ordering = ('ordem', 'id')

    def __str__(self):
        return self.texto


class ChecklistPerguntaOpcao(models.Model):
    pergunta = models.ForeignKey(
        ChecklistPergunta,
        on_delete=models.CASCADE,
        related_name='opcoes',
    )
    valor = models.CharField(max_length=255)
    ordem = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('ordem', 'id')

    def __str__(self):
        return self.valor


class ChecklistResposta(models.Model):
    formulario = models.ForeignKey(
        ChecklistFormulario,
        on_delete=models.PROTECT,
        related_name='respostas',
    )
    versao = models.ForeignKey(
        ChecklistFormularioVersao,
        on_delete=models.PROTECT,
        related_name='respostas',
    )
    maquina = models.ForeignKey(
        Maquina,
        on_delete=models.PROTECT,
        related_name='checklist_respostas',
    )
    funcionario = models.ForeignKey(
        'funcionario.Funcionario',
        on_delete=models.PROTECT,
        related_name='checklist_respostas',
    )
    data_referencia = models.DateField(default=date.today)
    observacoes = models.TextField(blank=True, null=True)
    imagem = models.ImageField(upload_to='checklists/respostas/', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-criado_em',)

    def __str__(self):
        return f'Resposta {self.id} - Form {self.formulario_id}'


class ChecklistRespostaItem(models.Model):
    resposta = models.ForeignKey(
        ChecklistResposta,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    pergunta = models.ForeignKey(
        ChecklistPergunta,
        on_delete=models.PROTECT,
        related_name='respostas_itens',
    )
    texto_resposta = models.TextField(blank=True, null=True)
    opcoes_selecionadas = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('resposta', 'pergunta')

    def __str__(self):
        return f'Resposta {self.resposta_id} / Pergunta {self.pergunta_id}'
