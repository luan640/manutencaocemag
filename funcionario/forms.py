from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

from funcionario.models import Funcionario

class LoginForm(forms.Form):
    matricula = forms.CharField(label='Matrícula', max_length=20)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)

    def clean(self):
        matricula = self.cleaned_data.get('matricula')
        password = self.cleaned_data.get('password')
        user = authenticate(matricula=matricula, password=password)
        
        if user is None:
            raise forms.ValidationError("Matrícula ou senha incorretos")
        return self.cleaned_data

    def get_user(self):
        matricula = self.cleaned_data.get('matricula')
        return authenticate(matricula=matricula, password=self.cleaned_data.get('password'))

class CadastroUsuarioForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Senha')
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirme a Senha')

    class Meta:
        model = Funcionario
        fields = ['matricula', 'nome', 'tipo_acesso', 'area']
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "As senhas não coincidem.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Salva a senha como hash
        if commit:
            user.save()
        return user
