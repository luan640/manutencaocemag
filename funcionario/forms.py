from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Funcionario
from django.contrib.auth import authenticate

class FuncionarioCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Senha', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirmação de senha', 
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Funcionario
        fields = ('matricula', 'nome', 'tipo_acesso', 'area', 'telefone')
        widgets = {
            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_acesso': forms.HiddenInput(),  # Oculta o campo tipo_acesso
            'area': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_acesso'].initial = 'solicitante'  # Define o valor padrão para tipo_acesso

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('As senhas não coincidem.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class FuncionarioChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Senha")

    class Meta:
        model = Funcionario
        fields = ('matricula', 'nome', 'password', 'is_active', 'is_staff', 'tipo_acesso', 'area', 'telefone')

    def clean_password(self):
        return self.initial['password']

class LoginForm(forms.Form):
    matricula = forms.CharField(label='Matrícula', max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        matricula = cleaned_data.get('matricula')
        password = cleaned_data.get('password')

        if matricula and password:
            self.user = authenticate(username=matricula, password=password)
            if self.user is None:
                raise forms.ValidationError('Matrícula ou senha incorretos.')
            elif not self.user.is_active:
                raise forms.ValidationError('Esta conta está inativa.')
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)
