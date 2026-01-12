from django import forms
from django.forms import modelformset_factory

from .models import PlanoPreventiva, TarefaPreventiva, SolicitacaoPreventiva

class PlanoPreventivaForm(forms.ModelForm):
    nome = forms.CharField(label='Nome do Plano', widget=forms.TextInput(attrs={'class': 'form-control'}))
    descricao = forms.CharField(label='Descrição', widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}))
    periodicidade = forms.IntegerField(label='Periodicidade (em dias)', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    dias_antecedencia = forms.IntegerField(help_text="Dias para abertura com antecedência",label='Abertura com antecedência de:', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    data_inicio = forms.DateField(label='Data para inicio da contagem',required=True,widget=forms.DateInput(attrs={'class': 'form-control','type': 'date'},format='%Y-%m-%d'))
    abertura_automatica = forms.BooleanField(label='Abertura Automática', required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    data_base = forms.DateField(label='Data da próxima abertura',required=True,widget=forms.DateInput(attrs={'class': 'form-control','type': 'date'},format='%Y-%m-%d'))

    class Meta:
        model = PlanoPreventiva
        fields = ['nome', 'descricao', 'periodicidade', 'dias_antecedencia','data_inicio','abertura_automatica','data_base']


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
