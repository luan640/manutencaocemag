from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Funcionario
from .forms import FuncionarioCreationForm, FuncionarioChangeForm

class FuncionarioAdmin(UserAdmin):
    add_form = FuncionarioCreationForm
    form = FuncionarioChangeForm
    model = Funcionario
    list_display = ('matricula', 'nome', 'tipo_acesso', 'is_staff')
    ordering = ('matricula',)
    fieldsets = (
        (None, {'fields': ('matricula', 'nome', 'password')}),
        ('Informações pessoais', {'fields': ('telefone', 'area')}),
        ('Permissões', {'fields': ('tipo_acesso', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('matricula', 'nome', 'password1', 'password2', 'tipo_acesso', 'area', 'telefone', 'is_staff', 'is_superuser'),
        }),
    )

admin.site.register(Funcionario, FuncionarioAdmin)
