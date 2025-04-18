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
