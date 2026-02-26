from django import forms
from .models import Execucao, InfoSolicitacao, MaquinaParada
from cadastro.models import Operador


class MaquinaParadaForm(forms.ModelForm):
    class Meta:
        model = MaquinaParada
        fields = ["execucao", "data_inicio", "data_fim"]
        widgets = {
            "data_inicio": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "form-control"},
            ),
            "data_fim": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "form-control"},
            ),
            "execucao": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_inicio"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["data_fim"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["data_fim"].required = False

        if self.instance and self.instance.pk and self.instance.ordem_id:
            self.fields["execucao"].queryset = Execucao.objects.filter(
                ordem=self.instance.ordem
            ).order_by("n_execucao")
        else:
            self.fields["execucao"].queryset = Execucao.objects.none()

        self.fields["execucao"].required = False

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get("data_inicio")
        data_fim = cleaned_data.get("data_fim")

        if data_inicio and data_fim and data_fim < data_inicio:
            self.add_error("data_fim", "A data fim deve ser maior ou igual à data início.")

        return cleaned_data

