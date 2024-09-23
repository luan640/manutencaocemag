from django import forms
from django.forms import modelformset_factory

from .models import PlanoPreventiva, TarefaPreventiva, SolicitacaoPreventiva

class PlanoPreventivaForm(forms.ModelForm):
    class Meta:
        model = PlanoPreventiva
        fields = ['nome', 'descricao', 'periodicidade', 'abertura_automatica']
        widgets = {
            'nome': forms.TextInput(attrs={'class':'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descrição do Plano', 'class':'form-control'}),
            'periodicidade': forms.NumberInput(attrs={'class':'form-control'})
        }

class TarefaPreventivaForm(forms.ModelForm):
    class Meta:
        model = TarefaPreventiva
        fields = ['descricao', 'responsabilidade']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Descrição da Tarefa', 'class':'form-control'}),
            'responsabilidade': forms.Select(attrs={'class':'form-control'})
        }

TarefaPreventivaFormSet = modelformset_factory(
    TarefaPreventiva,
    form=TarefaPreventivaForm,
    extra=0,
)

class SolicitacaoPreventivaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoPreventiva
        fields = ['ordem', 'plano', 'finalizada', 'data']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }
