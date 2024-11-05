from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

class FuncionarioManager(BaseUserManager):
    def create_user(self, matricula, nome, password=None, **extra_fields):
        if not matricula:
            raise ValueError('A matrícula é obrigatória.')
        if not nome:
            raise ValueError('O nome é obrigatório.')

        user = self.model(matricula=matricula, nome=nome, **extra_fields)
        print(user)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, matricula, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_acesso', self.model.ADMINISTRADOR)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário precisa ter is_superuser=True.')
        if extra_fields.get('tipo_acesso') != self.model.ADMINISTRADOR:
            raise ValueError('Superusuário precisa ser ADMINISTRADOR.')

        return self.create_user(matricula, nome, password, **extra_fields)

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
    telefone = models.CharField(max_length=13, blank=True, null=True)

    # Sobrescrever os campos groups e user_permissions para evitar conflitos
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='funcionario_set',  # Nome único para evitar conflito com 'auth.User.groups'
        blank=True,
        help_text='Os grupos aos quais o funcionário pertence.',
        verbose_name='grupos',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='funcionario_user_set',  # Nome único para evitar conflito com 'auth.User.user_permissions'
        blank=True,
        help_text='Permissões específicas para este funcionário.',
        verbose_name='permissões de funcionário',
    )

    USERNAME_FIELD = 'matricula'
    REQUIRED_FIELDS = ['nome']

    # Aqui é onde você adiciona o manager personalizado
    objects = FuncionarioManager()

    def __str__(self):
        return f'{self.matricula} - {self.nome}'

    def is_administrador(self):
        return self.tipo_acesso == self.ADMINISTRADOR

    def save(self, *args, **kwargs):
        # Adicionar "55" ao telefone, se necessário
        if self.telefone and not self.telefone.startswith('55'):
            self.telefone = '55' + self.telefone

        super(Funcionario, self).save(*args, **kwargs)
