from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import Funcionario


def nivel_minimo(tipo_acesso_minimo):
    """
    Decorator de view que exige que o usuário tenha, no mínimo, o nível de
    acesso do tipo_acesso informado (Funcionario.SOLICITANTE/OPERADOR/ADMINISTRADOR).
    is_staff/is_superuser sempre passam, independente do tipo_acesso.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            if not request.user.tem_nivel_minimo(tipo_acesso_minimo):
                messages.error(request, 'Você não tem permissão para acessar esta página.')
                return redirect('home_solicitante')

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# Atalhos para os níveis existentes
operador_required = nivel_minimo(Funcionario.OPERADOR)
admin_required = nivel_minimo(Funcionario.ADMINISTRADOR)
