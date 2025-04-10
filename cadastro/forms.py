from django import forms
from .models import Maquina, Operador
from cadastro.models import Operador

class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ['codigo', 'descricao', 'apelido', 'setor', 'tipo','tombamento', 'criticidade', 'maquina_critica', 'foto']
        widgets = {
            'codigo': forms.TextInput(attrs={'placeholder': 'Código da máquina', 'class':'form-control'}),
            'descricao': forms.TextInput(attrs={'placeholder': 'Descrição da Máquina', 'class':'form-control'}),
            'apelido': forms.TextInput(attrs={'placeholder': 'Apelido da Máquina', 'class':'form-control'}),
            'tombamento': forms.TextInput(attrs={'placeholder': 'Código de Tombamento', 'class':'form-control'}),
            'setor': forms.Select(attrs={'class':'form-select'}),
            'tipo': forms.Select(attrs={'class':'form-select'}),
            'criticidade': forms.Select(attrs={'class': 'form-select'}),
            'maquina_critica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control-file'})    

        }

class AddOperadorForm(forms.ModelForm):
    class Meta:
        model = Operador
        fields = ['nome', 'matricula', 'status', 'area']
        widgets = {
            'nome': forms.TextInput(attrs={'class':'form-control'}),
            'matricula': forms.TextInput(attrs={'class':'form-control'}),
            'area': forms.Select(attrs={'class':'form-control'}),
        }
