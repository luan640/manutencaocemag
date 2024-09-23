from django.contrib import admin

from .models import Maquina, Setor, Operador, TipoTarefas

admin.site.register(Maquina)
admin.site.register(Setor)
admin.site.register(Operador)
admin.site.register(TipoTarefas)
