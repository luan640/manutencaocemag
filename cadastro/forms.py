from django import forms
from .models import Maquina, Operador
from cadastro.models import Operador

class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ['codigo', 'descricao', 'apelido', 'setor', 'tombamento', 'criticidade', 'foto']
        widgets = {
            'codigo': forms.TextInput(attrs={'placeholder': 'Código da máquina', 'class':'form-control'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Descrição da Máquina', 'class':'form-control'}),
            'apelido': forms.TextInput(attrs={'placeholder': 'Apelido da Máquina', 'class':'form-control'}),
            'tombamento': forms.TextInput(attrs={'placeholder': 'Código de Tombamento', 'class':'form-control'}),
            'setor': forms.Select(attrs={'class':'form-select'}),
            'criticidade': forms.Select(attrs={'class': 'form-select'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }

class AddOperadorForm(forms.ModelForm):
    class Meta:
        model = Operador
        fields = ['nome', 'matricula', 'salario', 'status', 'area']
