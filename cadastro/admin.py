from django.contrib import admin

from .models import (
    ChecklistFormulario,
    ChecklistFormularioVersao,
    ChecklistPergunta,
    ChecklistPerguntaOpcao,
    ChecklistResposta,
    ChecklistRespostaItem,
    Maquina,
    Operador,
    Setor,
    TipoTarefas,
)

admin.site.register(Maquina)
admin.site.register(Setor)
admin.site.register(Operador)
admin.site.register(TipoTarefas)


class ChecklistPerguntaOpcaoInline(admin.TabularInline):
    model = ChecklistPerguntaOpcao
    extra = 0


@admin.register(ChecklistPergunta)
class ChecklistPerguntaAdmin(admin.ModelAdmin):
    list_display = ('id', 'versao', 'ordem', 'texto', 'tipo', 'obrigatoria')
    inlines = [ChecklistPerguntaOpcaoInline]


@admin.register(ChecklistFormulario)
class ChecklistFormularioAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'maquina', 'ativo', 'versao_atual', 'atualizado_em')
    list_filter = ('ativo', 'maquina__area')
    search_fields = ('titulo', 'maquina__codigo', 'maquina__descricao')


@admin.register(ChecklistFormularioVersao)
class ChecklistFormularioVersaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'formulario', 'numero', 'titulo', 'maquina', 'criado_em')
    list_filter = ('maquina__area',)
    search_fields = ('titulo', 'formulario__titulo', 'maquina__codigo')


class ChecklistRespostaItemInline(admin.TabularInline):
    model = ChecklistRespostaItem
    extra = 0
    readonly_fields = ('pergunta', 'texto_resposta', 'opcoes_selecionadas')


@admin.register(ChecklistResposta)
class ChecklistRespostaAdmin(admin.ModelAdmin):
    list_display = ('id', 'formulario', 'versao', 'maquina', 'funcionario', 'data_referencia', 'criado_em')
    list_filter = ('maquina__area', 'data_referencia')
    search_fields = ('formulario__titulo', 'funcionario__nome', 'funcionario__matricula', 'maquina__codigo')
    inlines = [ChecklistRespostaItemInline]
