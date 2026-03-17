from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


@login_required
def checklist_formulario_list(request):
    return redirect("checklists_manage_view")


@login_required
def checklist_formulario_criar(request):
    messages.info(
        request,
        "A gestao de checklists foi movida para a area central de checklists.",
    )
    return redirect("checklists_manage_view")


@login_required
def checklist_formulario_editar(request, formulario_id):
    messages.info(
        request,
        "A edicao de checklists foi movida para a area central de checklists.",
    )
    return redirect("checklists_manage_view")


@login_required
def checklist_formulario_excluir(request, formulario_id):
    messages.info(
        request,
        "A exclusao de checklists foi movida para a area central de checklists.",
    )
    return redirect("checklists_manage_view")


def checklist_publico(request, token_publico):
    return redirect(reverse("checklist_public_view", args=[token_publico]))


@login_required
def checklist_respostas_historico(request):
    return redirect("checklists_history_view")
