import json

from django import forms
from django.contrib.auth import get_user_model

from cadastro.models import Maquina


class ChecklistFormularioBuilderForm(forms.Form):
    titulo = forms.CharField(
        label="Titulo do formulario",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    maquina = forms.ModelChoiceField(
        label="Maquina",
        queryset=Maquina.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    perguntas_json = forms.CharField(
        required=True,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        maquinas = Maquina.objects.order_by("codigo")
        if user and getattr(user, "is_authenticated", False) and not user.is_staff:
            area = getattr(user, "area", None)
            if area:
                maquinas = maquinas.filter(area=area)
        self.fields["maquina"].queryset = maquinas

    def clean_perguntas_json(self):
        raw_value = self.cleaned_data.get("perguntas_json") or "[]"
        try:
            perguntas = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Formato de perguntas invalido.") from exc

        if not isinstance(perguntas, list) or not perguntas:
            raise forms.ValidationError("Adicione ao menos uma pergunta.")

        perguntas_normalizadas = []
        tipos_validos = {"texto", "escolha_unica", "multipla_escolha"}
        for idx, pergunta in enumerate(perguntas, start=1):
            if not isinstance(pergunta, dict):
                raise forms.ValidationError(f"Pergunta #{idx} invalida.")

            enunciado = (pergunta.get("enunciado") or "").strip()
            tipo = (pergunta.get("tipo") or "").strip()
            obrigatoria = bool(pergunta.get("obrigatoria", True))
            opcoes = pergunta.get("opcoes") or []

            if not enunciado:
                raise forms.ValidationError(f"Pergunta #{idx} sem enunciado.")
            if tipo not in tipos_validos:
                raise forms.ValidationError(f"Tipo invalido na pergunta #{idx}.")

            if tipo in {"escolha_unica", "multipla_escolha"}:
                if not isinstance(opcoes, list):
                    raise forms.ValidationError(f"Opcoes invalidas na pergunta #{idx}.")
                opcoes = [str(opcao).strip() for opcao in opcoes if str(opcao).strip()]
                if len(opcoes) < 2:
                    raise forms.ValidationError(
                        f"A pergunta #{idx} precisa de pelo menos 2 opcoes."
                    )
            else:
                opcoes = []

            perguntas_normalizadas.append(
                {
                    "enunciado": enunciado,
                    "tipo": tipo,
                    "obrigatoria": obrigatoria,
                    "opcoes": opcoes,
                }
            )

        return json.dumps(perguntas_normalizadas, ensure_ascii=False)


class ChecklistRespostaPublicaForm(forms.Form):
    funcionario = forms.ModelChoiceField(
        label="Funcionario",
        queryset=get_user_model().objects.filter(is_active=True).order_by("nome"),
        empty_label="Selecione",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    data_registro = forms.DateField(
        label="Data",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "readonly": "readonly"}),
    )
    observacoes = forms.CharField(
        label="Observacoes",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )
    imagem = forms.ImageField(
        label="Imagem obrigatoria",
        required=True,
        widget=forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
