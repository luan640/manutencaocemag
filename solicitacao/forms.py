from django import forms

from .models import Solicitacao, Foto

class SolicitacaoForm(forms.ModelForm):
    class Meta:
        model = Solicitacao
        fields = ['setor', 'equipamento_em_falha', 'maquina', 'tipo_ferramenta', 'codigo_ferramenta', 'setor_maq_solda', 'descricao', 'impacto_producao', 'maq_parada', 'video']
        widgets = {
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'equipamento_em_falha': forms.Select(attrs={'class': 'form-select'}),
            'maquina': forms.Select(attrs={'class': 'form-select'}),
            'tipo_ferramenta': forms.Select(attrs={'class': 'form-select'}),
            'codigo_ferramenta': forms.TextInput(attrs={'class': 'form-control'}),
            'setor_maq_solda': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control'}),
            'impacto_producao': forms.Select(attrs={'class': 'form-select'}),
            'maq_parada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SolicitacaoPredialForm(forms.ModelForm):
    class Meta:
        model = Solicitacao
        fields = ['setor','maquina','descricao','impacto_producao','video']
        widgets = {
            'setor': forms.Select(attrs={'class': 'form-select'}),
            'maquina': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control','placeholder':'Descreva o motivo da sua solicitação.'}),
            'impacto_producao': forms.Select(attrs={'class': 'form-select'}),
            'video': forms.Textarea(attrs={'class': 'form-control'}),
        }

class TarefaRotinaPredialForm(forms.ModelForm):
    class Meta:
        model = Solicitacao
        fields = ['tarefa','descricao','impacto_producao','video']
        widgets = {
            'tarefa': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control','placeholder':'Descreva o motivo da sua solicitação.'}),
        }


class MultipleFileInput(forms.FileInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs.update({'multiple': 'multiple', 'required':False})

class FotoForm(forms.Form):
    imagens = forms.FileField(widget=MultipleFileInput(), required=False)

