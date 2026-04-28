from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.urls import reverse
from django.utils.html import format_html

from .models import Funcionario


class BaseFuncionarioValidationMixin:
    def clean(self):
        cleaned_data = super().clean()
        tipo_acesso = cleaned_data.get('tipo_acesso')
        area = cleaned_data.get('area')

        if tipo_acesso in {Funcionario.ADMINISTRADOR, Funcionario.OPERADOR} and not area:
            self.add_error('area', 'Area e obrigatoria para administradores e operadores.')

        return cleaned_data


class FuncionarioCreationForm(BaseFuncionarioValidationMixin, forms.ModelForm):
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirmacao de senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model = Funcionario
        fields = ('matricula', 'nome', 'tipo_acesso', 'area', 'telefone')
        widgets = {
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_acesso': forms.HiddenInput(),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_acesso'].initial = Funcionario.SOLICITANTE
        self.fields['area'].required = False

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('As senhas nao coincidem.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class OperadorAccessForm(FuncionarioCreationForm):
    class Meta(FuncionarioCreationForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_acesso'].initial = Funcionario.OPERADOR
        self.fields['tipo_acesso'].widget = forms.HiddenInput()
        self.fields['area'].required = True
        self.fields['telefone'].required = False


class SolicitanteManagementCreateForm(FuncionarioCreationForm):
    class Meta(FuncionarioCreationForm.Meta):
        widgets = {
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_acesso': forms.HiddenInput(),
            'area': forms.HiddenInput(),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_acesso'].initial = Funcionario.SOLICITANTE
        self.fields['tipo_acesso'].widget = forms.HiddenInput()
        self.fields['area'].widget = forms.HiddenInput()
        self.fields['area'].required = False
        self.fields['area'].initial = ''
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('As senhas nao coincidem.')
        return password2

    def save(self, commit=True):
        user = super(FuncionarioCreationForm, self).save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class SolicitanteManagementUpdateForm(BaseFuncionarioValidationMixin, forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ('matricula', 'nome', 'telefone')
        widgets = {
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matricula'].widget.attrs['id'] = 'edit-matricula'
        self.fields['nome'].widget.attrs['id'] = 'edit-nome'
        self.fields['telefone'].widget.attrs['id'] = 'edit-telefone'
        self.fields['telefone'].widget.attrs['autocomplete'] = 'off'


class FuncionarioChangeForm(BaseFuncionarioValidationMixin, forms.ModelForm):
    password = ReadOnlyPasswordHashField(label='Senha')

    class Meta:
        model = Funcionario
        fields = ('matricula', 'nome', 'password', 'is_active', 'is_staff', 'tipo_acesso', 'area', 'telefone')
        widgets = {
            'area': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_password(self):
        return self.initial['password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            password_change_url = reverse('admin:auth_user_password_change', args=[self.instance.pk])
            self.fields['password'].help_text = format_html(
                'As senhas nao sao armazenadas em texto puro. '
                'Voce pode <a href="{}">alterar a senha deste usuario aqui</a>.',
                password_change_url,
            )


class LoginForm(forms.Form):
    matricula = forms.CharField(
        label='Matricula',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        matricula = cleaned_data.get('matricula')
        password = cleaned_data.get('password')

        if matricula and password:
            self.user = authenticate(username=matricula, password=password)
            if self.user is None:
                raise forms.ValidationError('Matricula ou senha incorretos.')
            if not self.user.is_active:
                raise forms.ValidationError('Esta conta esta inativa.')
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)
