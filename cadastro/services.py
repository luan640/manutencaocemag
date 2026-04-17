from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from cadastro.models import ChecklistFormulario, ChecklistRelatorioDestinatario, ChecklistResposta


def build_daily_autonomous_overview(report_date):
    responses = list(
        ChecklistResposta.objects.select_related(
            'formulario',
            'versao',
            'funcionario',
        )
        .filter(data_referencia=report_date)
        .order_by('versao__titulo', 'criado_em', 'funcionario__nome')
    )

    rows = [
        {
            'autonomous_name': response.versao.titulo,
            'created_at': response.criado_em,
            'employee_name': response.funcionario.nome,
        }
        for response in responses
    ]
    answered_form_ids = {response.formulario_id for response in responses}
    pending_forms = list(
        ChecklistFormulario.objects.select_related('maquina', 'versao_atual')
        .filter(ativo=True)
        .exclude(id__in=answered_form_ids)
        .order_by('titulo', 'maquina__codigo')
    )
    missing_rows = [
        {
            'autonomous_name': form.versao_atual.titulo if form.versao_atual else form.titulo,
            'machine_name': (
                f"{form.maquina.codigo} - {form.maquina.descricao}"
                if form.maquina.descricao
                else form.maquina.codigo
            ),
        }
        for form in pending_forms
    ]

    formatted_date = report_date.strftime('%d/%m/%Y')
    subject = f'Panorama de respostas das autônomas - {formatted_date}'
    context = {
        'report_date': report_date,
        'report_date_display': formatted_date,
        'rows': rows,
        'has_rows': bool(rows),
        'missing_rows': missing_rows,
        'has_missing_rows': bool(missing_rows),
        'response_count': len(rows),
        'missing_count': len(missing_rows),
    }
    return {
        'subject': subject,
        'context': context,
        'response_count': len(rows),
    }


def execute_daily_autonomous_overview(report_date, dry_run=False):
    recipients = list(
        ChecklistRelatorioDestinatario.objects.filter(ativo=True)
        .order_by('email')
        .values_list('email', flat=True)
    )

    overview = build_daily_autonomous_overview(report_date)
    result = {
        'report_date': report_date,
        'subject': overview['subject'],
        'response_count': overview['response_count'],
        'missing_count': overview['context']['missing_count'],
        'recipient_count': len(recipients),
        'dry_run': dry_run,
        'sent_count': 0,
        'skipped_reason': None,
    }

    if not recipients:
        result['skipped_reason'] = 'Nenhum destinatario ativo configurado.'
        return result

    if dry_run:
        return result

    mail_result = send_daily_autonomous_overview(report_date, recipients)
    result['sent_count'] = mail_result['sent_count']
    return result


def send_daily_autonomous_overview(report_date, recipients):
    overview = build_daily_autonomous_overview(report_date)
    context = overview['context']

    text_body = render_to_string('checklists/emails/daily_overview.txt', context)
    html_body = render_to_string('checklists/emails/daily_overview.html', context)

    message = EmailMultiAlternatives(
        subject=overview['subject'],
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')
    sent_count = message.send()

    return {
        'subject': overview['subject'],
        'response_count': overview['response_count'],
        'sent_count': sent_count,
        'generated_at': datetime.now(),
    }
