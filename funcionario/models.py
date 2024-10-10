from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class FuncionarioManager(BaseUserManager):
    def create_user(self, matricula, nome, tipo_acesso, area=None, password=None, **extra_fields):
        if not matricula:
            raise ValueError('A matrícula do funcionário deve ser fornecida')
        if not nome:
            raise ValueError('O nome do funcionário deve ser fornecido')
        if tipo_acesso not in ['solicitante', 'administrador','operador']:
            raise ValueError('Tipo de acesso inválido')
        if area not in [None, 'producao', 'predial']:
            raise ValueError('Área inválida')

        user = self.model(matricula=matricula, nome=nome, tipo_acesso=tipo_acesso, area=area, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, matricula, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')

        return self.create_user(matricula, nome, 'administrador', 'producao', password, **extra_fields)

class Funcionario(AbstractBaseUser, PermissionsMixin):
    SOLICITANTE = 'solicitante'
    ADMINISTRADOR = 'administrador'
    OPERADOR = 'operador'

    TIPO_ACESSO_CHOICES = [
        (SOLICITANTE, 'Solicitante'),
        (ADMINISTRADOR, 'Administrador'),
        (OPERADOR, 'Operador')
    ]

    AREA_CHOICES = [
        ('producao', 'Produção'),
        ('predial', 'Predial'),
    ]

    matricula = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=255)
    tipo_acesso = models.CharField(max_length=50, choices=TIPO_ACESSO_CHOICES, default=SOLICITANTE)
    area = models.CharField(max_length=50, choices=AREA_CHOICES, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    telefone = models.CharField(max_length=11, blank=True, null=True)

    USERNAME_FIELD = 'matricula'
    REQUIRED_FIELDS = ['nome']

    objects = FuncionarioManager()

    def __str__(self):
        return f'{self.matricula} - {self.nome}'

    def is_administrador(self):
        return self.tipo_acesso == self.ADMINISTRADOR
    
    def save(self, *args, **kwargs):
        # Adicionar "55" no início do telefone, se não estiver presente
        if self.telefone and not self.telefone.startswith('55'):
            self.telefone = '55' + self.telefone
        super(Funcionario, self).save(*args, **kwargs)

    

