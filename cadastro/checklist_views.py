import json
from datetime import date, datetime, timedelta
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from cadastro.models import (
    ChecklistFormulario,
    ChecklistFormularioVersao,
    ChecklistPergunta,
    ChecklistPerguntaOpcao,
    ChecklistRelatorioDestinatario,
    ChecklistResposta,
    ChecklistRespostaItem,
    Maquina,
)
from cadastro.services import execute_daily_autonomous_overview
from funcionario.models import Funcionario


TIPO_PERGUNTA_ALIAS = {
    ChecklistPergunta.TIPO_INPUT: ChecklistPergunta.TIPO_INPUT,
    'texto': ChecklistPergunta.TIPO_INPUT,
    'input_texto': ChecklistPergunta.TIPO_INPUT,
    'input': ChecklistPergunta.TIPO_INPUT,
    ChecklistPergunta.TIPO_ESCOLHA_UNICA: ChecklistPergunta.TIPO_ESCOLHA_UNICA,
    'escolha_unica': ChecklistPergunta.TIPO_ESCOLHA_UNICA,
    'single': ChecklistPergunta.TIPO_ESCOLHA_UNICA,
    'single_choice': ChecklistPergunta.TIPO_ESCOLHA_UNICA,
    ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA: ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
    'multipla_escolha': ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
    'multiple': ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
    'multiple_choice': ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
}


class SimplePDF:
    PAGE_WIDTH = 595
    PAGE_HEIGHT = 842
    MARGIN_X = 40
    MARGIN_TOP = 40
    MARGIN_BOTTOM = 40

    def __init__(self, title):
        self.title = title
        self.pages = []
        self.current = []
        self.y = self.PAGE_HEIGHT - self.MARGIN_TOP
        self.page_number = 0
        self.new_page()

    def _escape(self, text):
        text = str(text or "")
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return text.encode("cp1252", errors="replace").decode("latin-1")

    def new_page(self):
        if self.current:
            self.pages.append("\n".join(self.current))
        self.page_number += 1
        self.current = []
        self.y = self.PAGE_HEIGHT - self.MARGIN_TOP
        self.text(self.MARGIN_X, self.y, self.title, size=15)
        self.y -= 18
        self.text(self.MARGIN_X, self.y, f"Pagina {self.page_number}", size=9)
        self.y -= 18
        self.line(self.MARGIN_X, self.y, self.PAGE_WIDTH - self.MARGIN_X, self.y)
        self.y -= 14

    def ensure_space(self, height):
        if self.y - height < self.MARGIN_BOTTOM:
            self.new_page()

    def text(self, x, y, text, size=10):
        safe = self._escape(text)
        self.current.append(f"BT /F1 {size} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm ({safe}) Tj ET")

    def wrap_text(self, text, max_chars):
        text = str(text or "").strip()
        if not text:
            return [""]
        words = text.split()
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def write_paragraph(self, x, text, size=10, max_chars=85, line_height=13):
        lines = self.wrap_text(text, max_chars)
        self.ensure_space(len(lines) * line_height)
        for line in lines:
            self.text(x, self.y, line, size=size)
            self.y -= line_height
        return lines

    def line(self, x1, y1, x2, y2):
        self.current.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x, y, width, height):
        self.current.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re S")

    def draw_table(self, headers, rows, widths, row_height=18, header_height=20):
        table_width = sum(widths)
        x = self.MARGIN_X
        self.ensure_space(header_height)
        header_y = self.y
        self.rect(x, header_y - header_height, table_width, header_height)
        cursor = x
        for index, header in enumerate(headers):
            if index:
                self.line(cursor, header_y, cursor, header_y - header_height)
            self.text(cursor + 4, header_y - 14, header, size=9)
            cursor += widths[index]
        self.y -= header_height

        for row in rows:
            self.ensure_space(row_height)
            row_y = self.y
            self.rect(x, row_y - row_height, table_width, row_height)
            cursor = x
            for index, value in enumerate(row):
                if index:
                    self.line(cursor, row_y, cursor, row_y - row_height)
                self.text(cursor + 4, row_y - 13, value, size=9)
                cursor += widths[index]
            self.y -= row_height

    def build(self):
        if self.current:
            self.pages.append("\n".join(self.current))

        objects = []
        objects.append("<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(self.pages)))
        objects.append(f"<< /Type /Pages /Count {len(self.pages)} /Kids [{kids}] >>")
        font_id = 3 + len(self.pages) * 2

        for index, content in enumerate(self.pages):
            page_id = 3 + index * 2
            content_id = page_id + 1
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            )
            stream = f"q 0.2 w\n{content}\nQ".encode("latin-1")
            objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream")

        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{idx} 0 obj\n{obj}\nendobj\n".encode("latin-1"))
        xref_pos = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buffer.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode(
                "latin-1"
            )
        )
        buffer.seek(0)
        return buffer


def _is_management_user(user):
    return user.is_authenticated and (
        user.is_staff
        or getattr(user, 'tipo_acesso', None) in {
            Funcionario.ADMINISTRADOR,
            Funcionario.OPERADOR,
        }
    )


def _permission_denied():
    return JsonResponse({'error': 'Sem permissao para gerenciar checklists.'}, status=403)


def _is_report_admin_user(user):
    return user.is_authenticated and (
        user.is_staff or getattr(user, 'tipo_acesso', None) == Funcionario.ADMINISTRADOR
    )


def _report_permission_denied():
    return JsonResponse({'error': 'Sem permissao para gerenciar destinatarios do relatorio.'}, status=403)


def _delete_response_files(queryset):
    for resposta in queryset.only('id', 'imagem'):
        if resposta.imagem:
            resposta.imagem.delete(save=False)


def _parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        raise ValueError('JSON invalido.')


def _get_payload(request):
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        return _parse_json_body(request)
    payload = request.POST.dict()
    return payload


def _normalize_question_type(raw_type):
    if raw_type is None:
        return None
    normalized = TIPO_PERGUNTA_ALIAS.get(str(raw_type).strip().lower())
    return normalized


def _serialize_report_recipient(recipient):
    return {
        'id': recipient.id,
        'email': recipient.email,
        'name': recipient.nome_opcional,
        'active': recipient.ativo,
        'created_at': recipient.criado_em.isoformat(),
        'updated_at': recipient.atualizado_em.isoformat(),
    }


def _normalize_report_recipient_payload(payload):
    email = str(payload.get('email') or '').strip().lower()
    name = str(payload.get('name') or payload.get('nome_opcional') or '').strip()
    active = _to_bool(payload.get('active', payload.get('ativo', True)), default=True)

    if not email:
        raise ValueError('E-mail e obrigatorio.')

    return {
        'email': email,
        'nome_opcional': name or None,
        'ativo': active,
    }


def _parse_report_date(raw_value):
    if not raw_value:
        return timezone.now().date()
    try:
        return datetime.strptime(str(raw_value), '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('Use date no formato YYYY-MM-DD.') from exc


def _extract_internal_job_token(request):
    return (
        request.headers.get('X-Job-Token')
        or request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        or request.GET.get('token')
        or request.POST.get('token')
        or ''
    ).strip()


def _to_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {'true', '1', 'sim', 'yes'}:
        return True
    if normalized in {'false', '0', 'nao', 'não', 'no'}:
        return False
    return default


def _normalize_questions(raw_questions):
    if isinstance(raw_questions, str):
        try:
            raw_questions = json.loads(raw_questions)
        except json.JSONDecodeError as exc:
            raise ValueError('Campo "questions" precisa ser um JSON valido.') from exc

    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError('E necessario informar ao menos uma pergunta.')

    normalized_questions = []
    for index, raw_question in enumerate(raw_questions, start=1):
        if not isinstance(raw_question, dict):
            raise ValueError(f'Pergunta na posicao {index} esta invalida.')

        texto = str(raw_question.get('text') or raw_question.get('texto') or '').strip()
        if not texto:
            raise ValueError(f'Pergunta na posicao {index} sem texto.')

        tipo = _normalize_question_type(raw_question.get('type') or raw_question.get('tipo'))
        if tipo is None:
            raise ValueError(f'Pergunta "{texto}" com tipo invalido.')

        obrigatoria = _to_bool(raw_question.get('required', raw_question.get('obrigatoria', True)), default=True)

        opcoes = raw_question.get('options', raw_question.get('opcoes', [])) or []
        if isinstance(opcoes, str):
            try:
                opcoes = json.loads(opcoes)
            except json.JSONDecodeError:
                opcoes = [item.strip() for item in opcoes.split(',') if item.strip()]

        if tipo in {ChecklistPergunta.TIPO_ESCOLHA_UNICA, ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA}:
            if not isinstance(opcoes, list):
                raise ValueError(f'Pergunta "{texto}" precisa de opcoes em lista.')
            cleaned_options = []
            for option in opcoes:
                option_value = str(option).strip()
                if option_value and option_value not in cleaned_options:
                    cleaned_options.append(option_value)
            if len(cleaned_options) < 1:
                raise ValueError(f'Pergunta "{texto}" precisa de pelo menos 1 opcao.')
        else:
            cleaned_options = []

        normalized_questions.append(
            {
                'ordem': int(raw_question.get('order', raw_question.get('ordem', index))),
                'texto': texto,
                'tipo': tipo,
                'obrigatoria': obrigatoria,
                'opcoes': cleaned_options,
            }
        )

    normalized_questions.sort(key=lambda item: item['ordem'])
    return normalized_questions


def _serialize_question(pergunta):
    return {
        'id': pergunta.id,
        'order': pergunta.ordem,
        'text': pergunta.texto,
        'type': pergunta.tipo,
        'required': pergunta.obrigatoria,
        'options': [
            {
                'id': opcao.id,
                'value': opcao.valor,
                'order': opcao.ordem,
            }
            for opcao in pergunta.opcoes.all()
        ],
    }


def _serialize_version(versao):
    perguntas = versao.perguntas.all()
    return {
        'id': versao.id,
        'number': versao.numero,
        'title': versao.titulo,
        'machine': {
            'id': versao.maquina.id,
            'codigo': versao.maquina.codigo,
            'descricao': versao.maquina.descricao,
        },
        'created_at': versao.criado_em.isoformat(),
        'questions': [_serialize_question(pergunta) for pergunta in perguntas],
    }


def _serialize_form(formulario, request=None):
    public_url = None
    if request is not None:
        public_url = request.build_absolute_uri(
            reverse('checklist_public_view', kwargs={'token': formulario.token_publico})
        )

    return {
        'id': formulario.id,
        'title': formulario.titulo,
        'machine': {
            'id': formulario.maquina.id,
            'codigo': formulario.maquina.codigo,
            'descricao': formulario.maquina.descricao,
        },
        'active': formulario.ativo,
        'public_token': str(formulario.token_publico),
        'public_url': public_url,
        'current_version': formulario.versao_atual.numero if formulario.versao_atual else None,
        'created_at': formulario.criado_em.isoformat(),
        'updated_at': formulario.atualizado_em.isoformat(),
    }


def _clone_questions_from_version(versao):
    cloned_questions = []
    for pergunta in versao.perguntas.all():
        cloned_questions.append(
            {
                'ordem': pergunta.ordem,
                'texto': pergunta.texto,
                'tipo': pergunta.tipo,
                'obrigatoria': pergunta.obrigatoria,
                'opcoes': [opcao.valor for opcao in pergunta.opcoes.all()],
            }
        )
    return cloned_questions


def _create_new_version(formulario, titulo, maquina, questions, user):
    next_version_number = (formulario.versoes.order_by('-numero').values_list('numero', flat=True).first() or 0) + 1
    versao = ChecklistFormularioVersao.objects.create(
        formulario=formulario,
        numero=next_version_number,
        titulo=titulo,
        maquina=maquina,
        criado_por=user if user.is_authenticated else None,
    )

    for question in questions:
        pergunta = ChecklistPergunta.objects.create(
            versao=versao,
            ordem=question['ordem'],
            texto=question['texto'],
            tipo=question['tipo'],
            obrigatoria=question['obrigatoria'],
        )
        for option_index, option_value in enumerate(question['opcoes'], start=1):
            ChecklistPerguntaOpcao.objects.create(
                pergunta=pergunta,
                valor=option_value,
                ordem=option_index,
            )

    formulario.titulo = titulo
    formulario.maquina = maquina
    formulario.versao_atual = versao
    formulario.save(update_fields=['titulo', 'maquina', 'versao_atual', 'atualizado_em'])
    return versao


@login_required
def checklists_manage_view(request):
    if not _is_management_user(request.user):
        raise Http404
    maquinas = Maquina.objects.order_by('codigo')
    return render(
        request,
        'checklists/manage_forms.html',
        {
            'maquinas': maquinas,
        },
    )


@login_required
def checklists_history_view(request):
    if not _is_management_user(request.user):
        raise Http404
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)
    maquinas = Maquina.objects.order_by('codigo')
    formularios = (
        ChecklistFormulario.objects.select_related('maquina', 'versao_atual')
        .order_by('titulo')
    )
    respostas = ChecklistResposta.objects.all()
    return render(
        request,
        'checklists/history.html',
        {
            'maquinas': maquinas,
            'formularios': formularios,
            'indicadores': {
                'hoje': respostas.filter(data_referencia=hoje).count(),
                'semana': respostas.filter(data_referencia__gte=inicio_semana, data_referencia__lte=hoje).count(),
                'mes': respostas.filter(data_referencia__gte=inicio_mes, data_referencia__lte=hoje).count(),
            },
        },
    )


@login_required
def checklists_calendar_view(request):
    if not _is_management_user(request.user):
        raise Http404
    maquinas = Maquina.objects.order_by('codigo')
    return render(
        request,
        'checklists/calendar.html',
        {
            'maquinas': maquinas,
        },
    )


@login_required
def checklists_report_recipients_view(request):
    if not _is_report_admin_user(request.user):
        raise Http404
    recipients = ChecklistRelatorioDestinatario.objects.order_by('email')
    return render(
        request,
        'checklists/report_recipients.html',
        {
            'recipient_count': recipients.count(),
            'active_recipient_count': recipients.filter(ativo=True).count(),
        },
    )


@login_required
def api_checklist_forms(request):
    if not _is_management_user(request.user):
        return _permission_denied()

    if request.method == 'GET':
        queryset = ChecklistFormulario.objects.select_related('maquina', 'versao_atual').all()
        maquina_id = request.GET.get('maquina_id')
        active = request.GET.get('active')

        if maquina_id:
            queryset = queryset.filter(maquina_id=maquina_id)
        if active in {'true', 'false'}:
            queryset = queryset.filter(ativo=(active == 'true'))

        return JsonResponse(
            {'forms': [_serialize_form(formulario, request) for formulario in queryset]},
            status=200,
        )

    if request.method == 'POST':
        try:
            payload = _get_payload(request)
            title = str(payload.get('title') or payload.get('titulo') or '').strip()
            machine_id = payload.get('machine_id') or payload.get('maquina_id')
            raw_questions = payload.get('questions') or payload.get('perguntas')

            if not title:
                return JsonResponse({'error': 'Titulo e obrigatorio.'}, status=400)
            if not machine_id:
                return JsonResponse({'error': 'Maquina e obrigatoria.'}, status=400)

            machine = get_object_or_404(Maquina, pk=machine_id)
            questions = _normalize_questions(raw_questions)

            with transaction.atomic():
                formulario = ChecklistFormulario.objects.create(
                    titulo=title,
                    maquina=machine,
                    criado_por=request.user,
                    ativo=True,
                )
                versao = _create_new_version(formulario, title, machine, questions, request.user)

            versao = (
                ChecklistFormularioVersao.objects.select_related('maquina')
                .prefetch_related('perguntas__opcoes')
                .get(pk=versao.id)
            )
            return JsonResponse(
                {
                    'form': _serialize_form(formulario, request),
                    'version': _serialize_version(versao),
                },
                status=201,
            )
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)


@login_required
def api_checklist_calendar(request):
    if not _is_management_user(request.user):
        return _permission_denied()
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    queryset = ChecklistResposta.objects.select_related(
        'formulario',
        'versao',
        'maquina',
        'funcionario',
    ).all()

    machine_id = request.GET.get('maquina_id')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    if machine_id:
        queryset = queryset.filter(maquina_id=machine_id)
    if start_date:
        queryset = queryset.filter(data_referencia__gte=start_date)
    if end_date:
        queryset = queryset.filter(data_referencia__lte=end_date)

    events = []
    for response in queryset.order_by('data_referencia', 'maquina__codigo', 'funcionario__nome'):
        machine_label = response.maquina.codigo
        if response.maquina.descricao:
            machine_label = f"{machine_label} - {response.maquina.descricao}"
        events.append(
            {
                'id': response.id,
                'title': f"{response.maquina.codigo} | {response.funcionario.nome}",
                'start': response.data_referencia.isoformat(),
                'allDay': True,
                'url': f"{reverse('checklist_response_pdf', kwargs={'response_id': response.id})}?download=1",
                'extendedProps': {
                    'form_title': response.versao.titulo,
                    'form_version': response.versao.numero,
                    'machine_label': machine_label,
                    'employee_name': response.funcionario.nome,
                    'employee_badge': response.funcionario.matricula,
                    'notes': response.observacoes or '-',
                    'image_url': response.imagem.url if response.imagem else '',
                    'created_at': response.criado_em.strftime('%d/%m/%Y %H:%M'),
                },
            }
        )

    return JsonResponse({'events': events}, status=200)


@login_required
def api_checklist_report_recipients(request):
    if not _is_report_admin_user(request.user):
        return _report_permission_denied()

    if request.method == 'GET':
        recipients = ChecklistRelatorioDestinatario.objects.order_by('email')
        return JsonResponse(
            {'recipients': [_serialize_report_recipient(recipient) for recipient in recipients]},
            status=200,
        )

    if request.method == 'POST':
        try:
            payload = _get_payload(request)
            normalized = _normalize_report_recipient_payload(payload)
            recipient = ChecklistRelatorioDestinatario.objects.create(**normalized)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except IntegrityError:
            return JsonResponse({'error': 'Ja existe um destinatario com este e-mail.'}, status=400)

        return JsonResponse({'recipient': _serialize_report_recipient(recipient)}, status=201)

    return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)


@login_required
def api_checklist_report_recipient_detail(request, recipient_id):
    if not _is_report_admin_user(request.user):
        return _report_permission_denied()

    recipient = get_object_or_404(ChecklistRelatorioDestinatario, pk=recipient_id)

    if request.method == 'PUT':
        try:
            payload = _get_payload(request)
            normalized = _normalize_report_recipient_payload(payload)
            for field, value in normalized.items():
                setattr(recipient, field, value)
            recipient.save()
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except IntegrityError:
            return JsonResponse({'error': 'Ja existe um destinatario com este e-mail.'}, status=400)

        return JsonResponse({'recipient': _serialize_report_recipient(recipient)}, status=200)

    if request.method == 'PATCH':
        try:
            payload = _get_payload(request)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        action = str(payload.get('action') or '').strip().lower()
        if action not in {'activate', 'inactivate'}:
            return JsonResponse({'error': 'Acao invalida.'}, status=400)

        recipient.ativo = action == 'activate'
        recipient.save(update_fields=['ativo', 'atualizado_em'])
        return JsonResponse({'recipient': _serialize_report_recipient(recipient)}, status=200)

    if request.method == 'DELETE':
        recipient.delete()
        return JsonResponse({'message': 'Destinatario excluido com sucesso.'}, status=200)

    return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)


@csrf_exempt
def internal_send_daily_autonomous_overview(request):
    if request.method not in {'GET', 'POST'}:
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    configured_token = (getattr(settings, 'INTERNAL_JOB_TOKEN', '') or '').strip()
    if not configured_token:
        return JsonResponse({'error': 'INTERNAL_JOB_TOKEN nao configurado.'}, status=503)

    provided_token = _extract_internal_job_token(request)
    if provided_token != configured_token:
        return JsonResponse({'error': 'Token invalido.'}, status=403)

    try:
        report_date = _parse_report_date(request.GET.get('date') or request.POST.get('date'))
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    dry_run = _to_bool(request.GET.get('dry_run') or request.POST.get('dry_run'), default=False)
    result = execute_daily_autonomous_overview(report_date, dry_run=dry_run)

    status_code = 200 if not result['skipped_reason'] else 202
    return JsonResponse(
        {
            'message': 'Execucao concluida.',
            'report_date': report_date.isoformat(),
            'dry_run': dry_run,
            'response_count': result['response_count'],
            'missing_count': result['missing_count'],
            'recipient_count': result['recipient_count'],
            'sent_count': result['sent_count'],
            'skipped_reason': result['skipped_reason'],
        },
        status=status_code,
    )


@login_required
def api_checklist_form_detail(request, form_id):
    if not _is_management_user(request.user):
        return _permission_denied()

    formulario = get_object_or_404(
        ChecklistFormulario.objects.select_related('maquina', 'versao_atual'),
        pk=form_id,
    )

    if request.method == 'GET':
        if not formulario.versao_atual_id:
            return JsonResponse({'error': 'Formulario sem versao publicada.'}, status=409)
        versao = (
            ChecklistFormularioVersao.objects.select_related('maquina')
            .prefetch_related('perguntas__opcoes')
            .get(pk=formulario.versao_atual_id)
        )
        return JsonResponse(
            {'form': _serialize_form(formulario, request), 'version': _serialize_version(versao)},
            status=200,
        )

    if request.method == 'PUT':
        try:
            payload = _get_payload(request)

            new_title = str(payload.get('title') or payload.get('titulo') or formulario.titulo).strip()
            machine_id = payload.get('machine_id') or payload.get('maquina_id') or formulario.maquina_id
            if not new_title:
                return JsonResponse({'error': 'Titulo e obrigatorio.'}, status=400)

            machine = get_object_or_404(Maquina, pk=machine_id)

            raw_questions = payload.get('questions', payload.get('perguntas'))
            if not formulario.versao_atual_id:
                return JsonResponse({'error': 'Formulario sem versao publicada.'}, status=409)
            current_version = (
                ChecklistFormularioVersao.objects.select_related('maquina')
                .prefetch_related('perguntas__opcoes')
                .get(pk=formulario.versao_atual_id)
            )

            if raw_questions is None:
                questions = _clone_questions_from_version(current_version)
            else:
                questions = _normalize_questions(raw_questions)

            with transaction.atomic():
                versao = _create_new_version(formulario, new_title, machine, questions, request.user)

            versao = (
                ChecklistFormularioVersao.objects.select_related('maquina')
                .prefetch_related('perguntas__opcoes')
                .get(pk=versao.id)
            )
            return JsonResponse(
                {'form': _serialize_form(formulario, request), 'version': _serialize_version(versao)},
                status=200,
            )
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    if request.method == 'PATCH':
        try:
            payload = _get_payload(request)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        action = str(payload.get('action') or '').strip().lower()
        if action not in {'inactivate', 'activate'}:
            return JsonResponse({'error': 'Acao invalida.'}, status=400)

        formulario.ativo = action == 'activate'
        formulario.save(update_fields=['ativo', 'atualizado_em'])
        return JsonResponse(
            {
                'message': 'Checklist ativado com sucesso.' if formulario.ativo else 'Checklist inativado com sucesso.',
                'form': _serialize_form(formulario, request),
            },
            status=200,
        )

    if request.method == 'DELETE':
        respostas = ChecklistResposta.objects.filter(formulario=formulario)
        with transaction.atomic():
            _delete_response_files(respostas)
            respostas.delete()
            formulario.delete()
        return JsonResponse({'message': 'Checklist excluido com sucesso.'}, status=200)

    return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)


@login_required
def api_checklist_reset(request):
    if not _is_management_user(request.user):
        return _permission_denied()
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    respostas = ChecklistResposta.objects.all()
    formularios = ChecklistFormulario.objects.all()
    respostas_count = respostas.count()
    formularios_count = formularios.count()

    with transaction.atomic():
        _delete_response_files(respostas)
        respostas.delete()
        formularios.delete()

    return JsonResponse(
        {
            'message': 'Checklists zerados com sucesso.',
            'deleted_forms': formularios_count,
            'deleted_responses': respostas_count,
        },
        status=200,
    )


@login_required
def api_checklist_form_versions(request, form_id):
    if not _is_management_user(request.user):
        return _permission_denied()
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    formulario = get_object_or_404(ChecklistFormulario, pk=form_id)
    versoes = (
        formulario.versoes.select_related('maquina')
        .prefetch_related('perguntas__opcoes')
        .order_by('-numero')
    )
    return JsonResponse({'versions': [_serialize_version(versao) for versao in versoes]}, status=200)


def checklist_public_view(request, token):
    formulario = get_object_or_404(
        ChecklistFormulario.objects.select_related('versao_atual', 'maquina'),
        token_publico=token,
        ativo=True,
    )
    if not formulario.versao_atual_id:
        raise Http404
    versao_atual = (
        ChecklistFormularioVersao.objects.select_related('maquina')
        .prefetch_related('perguntas__opcoes')
        .get(pk=formulario.versao_atual_id)
    )
    funcionarios = Funcionario.objects.filter(is_active=True).order_by('nome')
    return render(
        request,
        'checklists/public_fill.html',
        {
            'formulario': formulario,
            'versao_atual': versao_atual,
            'token_publico': formulario.token_publico,
            'funcionarios': funcionarios,
            'hoje': date.today(),
        },
    )


def api_checklist_public_form(request, token):
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    formulario = get_object_or_404(
        ChecklistFormulario.objects.select_related('versao_atual', 'maquina'),
        token_publico=token,
        ativo=True,
    )
    if not formulario.versao_atual_id:
        return JsonResponse({'error': 'Formulario sem versao publicada.'}, status=409)
    versao = (
        ChecklistFormularioVersao.objects.select_related('maquina')
        .prefetch_related('perguntas__opcoes')
        .get(pk=formulario.versao_atual_id)
    )
    return JsonResponse(
        {
            'form': _serialize_form(formulario, request),
            'version': _serialize_version(versao),
            'employees_endpoint': request.build_absolute_uri(
                reverse('api_checklist_public_funcionarios', kwargs={'token': token})
            ),
        },
        status=200,
    )


def api_checklist_public_funcionarios(request, token):
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    formulario = get_object_or_404(ChecklistFormulario, token_publico=token, ativo=True)
    search = request.GET.get('search', '').strip()
    limit = int(request.GET.get('limit', 25))

    funcionarios = Funcionario.objects.filter(is_active=True)
    if search:
        funcionarios = funcionarios.filter(Q(nome__icontains=search) | Q(matricula__icontains=search))
    funcionarios = funcionarios.order_by('nome')[:limit]

    return JsonResponse(
        {
            'form_id': formulario.id,
            'employees': list(funcionarios.values('id', 'nome', 'matricula')),
        },
        status=200,
    )


def _extract_answers(payload):
    answers = payload.get('answers', {})
    if isinstance(answers, str):
        try:
            answers = json.loads(answers)
        except json.JSONDecodeError as exc:
            raise ValueError('Campo "answers" precisa ser JSON valido.') from exc
    if not isinstance(answers, dict):
        raise ValueError('Campo "answers" precisa ser um objeto.')
    return answers


def _normalize_choice_values(question, raw_value, multiple):
    if raw_value in (None, '', []):
        return []

    if multiple:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
    else:
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        if len(values) > 1:
            raise ValueError(f'Pergunta "{question.texto}" aceita apenas 1 escolha.')

    option_by_id = {str(opcao.id): opcao.valor for opcao in question.opcoes.all()}
    option_values = {opcao.valor: opcao.valor for opcao in question.opcoes.all()}

    normalized = []
    for value in values:
        value_str = str(value).strip()
        if not value_str:
            continue
        selected = option_by_id.get(value_str, option_values.get(value_str))
        if not selected:
            raise ValueError(f'Opcao invalida para a pergunta "{question.texto}".')
        if selected not in normalized:
            normalized.append(selected)
    return normalized


@csrf_exempt
def api_checklist_public_submit(request, token):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    formulario = get_object_or_404(
        ChecklistFormulario.objects.select_related('versao_atual', 'maquina'),
        token_publico=token,
        ativo=True,
    )
    if not formulario.versao_atual_id:
        return JsonResponse({'error': 'Formulario sem versao publicada.'}, status=409)
    versao = (
        ChecklistFormularioVersao.objects.select_related('maquina')
        .prefetch_related('perguntas__opcoes')
        .get(pk=formulario.versao_atual_id)
    )

    try:
        payload = _get_payload(request)
        funcionario_id = payload.get('employee_id') or payload.get('funcionario_id')
        if not funcionario_id:
            return JsonResponse({'error': 'Funcionario e obrigatorio.'}, status=400)

        funcionario = get_object_or_404(Funcionario, pk=funcionario_id, is_active=True)
        observacoes = (payload.get('notes') or payload.get('observacoes') or '').strip()
        data_raw = payload.get('date') or payload.get('data_referencia')
        data_referencia = timezone.now().date()
        if data_raw:
            try:
                data_referencia = datetime.strptime(str(data_raw), '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Data invalida. Use YYYY-MM-DD.'}, status=400)

        imagem = request.FILES.get('image') or request.FILES.get('imagem')
        if not imagem:
            return JsonResponse({'error': 'Imagem e obrigatoria.'}, status=400)

        answers_payload = _extract_answers(payload)
        perguntas = list(versao.perguntas.all())
        normalized_items = []

        for pergunta in perguntas:
            answer_raw = answers_payload.get(str(pergunta.id))
            if answer_raw is None:
                answer_raw = answers_payload.get(pergunta.id)

            if pergunta.tipo == ChecklistPergunta.TIPO_INPUT:
                texto = '' if answer_raw is None else str(answer_raw).strip()
                if pergunta.obrigatoria and not texto:
                    raise ValueError(f'A pergunta "{pergunta.texto}" e obrigatoria.')
                normalized_items.append(
                    {
                        'pergunta': pergunta,
                        'texto_resposta': texto or None,
                        'opcoes_selecionadas': [],
                    }
                )
                continue

            multiple = pergunta.tipo == ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA
            selected_options = _normalize_choice_values(pergunta, answer_raw, multiple=multiple)
            if pergunta.obrigatoria and not selected_options:
                raise ValueError(f'A pergunta "{pergunta.texto}" e obrigatoria.')

            normalized_items.append(
                {
                    'pergunta': pergunta,
                    'texto_resposta': None,
                    'opcoes_selecionadas': selected_options,
                }
            )

        with transaction.atomic():
            resposta = ChecklistResposta.objects.create(
                formulario=formulario,
                versao=versao,
                maquina=versao.maquina,
                funcionario=funcionario,
                data_referencia=data_referencia,
                observacoes=observacoes,
                imagem=imagem,
            )

            ChecklistRespostaItem.objects.bulk_create(
                [
                    ChecklistRespostaItem(
                        resposta=resposta,
                        pergunta=item['pergunta'],
                        texto_resposta=item['texto_resposta'],
                        opcoes_selecionadas=item['opcoes_selecionadas'],
                    )
                    for item in normalized_items
                ]
            )

        return JsonResponse(
            {
                'message': 'Checklist enviado com sucesso.',
                'response_id': resposta.id,
                'date': resposta.data_referencia.isoformat(),
            },
            status=201,
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@login_required
def api_checklist_responses(request):
    if not _is_management_user(request.user):
        return _permission_denied()
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    queryset = ChecklistResposta.objects.select_related(
        'formulario',
        'versao',
        'maquina',
        'funcionario',
    ).all()

    machine_id = request.GET.get('maquina_id')
    form_id = request.GET.get('form_id')
    employee_id = request.GET.get('employee_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if machine_id:
        queryset = queryset.filter(maquina_id=machine_id)
    if form_id:
        queryset = queryset.filter(formulario_id=form_id)
    if employee_id:
        queryset = queryset.filter(funcionario_id=employee_id)
    if start_date:
        queryset = queryset.filter(data_referencia__gte=start_date)
    if end_date:
        queryset = queryset.filter(data_referencia__lte=end_date)

    responses = []
    for response in queryset:
        responses.append(
            {
                'id': response.id,
                'form': {
                    'id': response.formulario_id,
                    'title': response.versao.titulo,
                    'version': response.versao.numero,
                },
                'machine': {
                    'id': response.maquina_id,
                    'codigo': response.maquina.codigo,
                    'descricao': response.maquina.descricao,
                },
                'employee': {
                    'id': response.funcionario_id,
                    'nome': response.funcionario.nome,
                    'matricula': response.funcionario.matricula,
                },
                'date': response.data_referencia.isoformat(),
                'notes': response.observacoes,
                'image_url': response.imagem.url if response.imagem else None,
                'created_at': response.criado_em.isoformat(),
            }
        )

    return JsonResponse({'responses': responses}, status=200)


@login_required
def api_checklist_response_detail(request, response_id):
    if not _is_management_user(request.user):
        return _permission_denied()
    if request.method != 'GET':
        return JsonResponse({'error': 'Metodo nao permitido.'}, status=405)

    response = get_object_or_404(
        ChecklistResposta.objects.select_related('formulario', 'versao', 'maquina', 'funcionario').prefetch_related(
            'itens__pergunta__opcoes'
        ),
        pk=response_id,
    )

    items = []
    for item in response.itens.all():
        items.append(
            {
                'question': {
                    'id': item.pergunta_id,
                    'text': item.pergunta.texto,
                    'type': item.pergunta.tipo,
                },
                'text_answer': item.texto_resposta,
                'selected_options': item.opcoes_selecionadas,
            }
        )

    return JsonResponse(
        {
            'response': {
                'id': response.id,
                'form': {
                    'id': response.formulario_id,
                    'title': response.versao.titulo,
                    'version': response.versao.numero,
                },
                'machine': {
                    'id': response.maquina_id,
                    'codigo': response.maquina.codigo,
                    'descricao': response.maquina.descricao,
                },
                'employee': {
                    'id': response.funcionario_id,
                    'nome': response.funcionario.nome,
                    'matricula': response.funcionario.matricula,
                },
                'date': response.data_referencia.isoformat(),
                'notes': response.observacoes,
                'image_url': response.imagem.url if response.imagem else None,
                'answers': items,
            }
        },
        status=200,
    )


@login_required
def checklist_qrcode_view(request, form_id):
    if not _is_management_user(request.user):
        raise Http404

    formulario = get_object_or_404(
        ChecklistFormulario.objects.select_related('maquina', 'versao_atual'),
        pk=form_id,
    )
    public_url = request.build_absolute_uri(
        reverse('checklist_public_view', kwargs={'token': formulario.token_publico})
    )
    return render(
        request,
        'checklists/qrcode.html',
        {
            'formulario': formulario,
            'public_url': public_url,
        },
    )


@login_required
def checklist_response_pdf(request, response_id):
    if not _is_management_user(request.user):
        raise Http404

    response = get_object_or_404(
        ChecklistResposta.objects.select_related('formulario', 'versao', 'maquina', 'funcionario').prefetch_related(
            'itens__pergunta__opcoes'
        ),
        pk=response_id,
    )

    pdf = SimplePDF(f"Relatório de Checklist Autônomo #{response.id}")

    pdf.text(40, pdf.y, "Identificação", size=12)
    pdf.y -= 14
    pdf.draw_table(
        ["Campo", "Valor"],
        [
            ["Formulário", f"{response.versao.titulo} (v{response.versao.numero})"],
            ["Máquina", f"{response.maquina.codigo} - {response.maquina.descricao or '-'}"],
            ["Funcionário", f"{response.funcionario.nome} - {response.funcionario.matricula}"],
            ["Data de referência", response.data_referencia.strftime("%d/%m/%Y")],
            ["Registrado em", response.criado_em.strftime("%d/%m/%Y %H:%M")],
            ["Observações", (response.observacoes or "-")[:80]],
            ["Imagem", response.imagem.url if response.imagem else "Não anexada"],
        ],
        [150, 365],
    )
    pdf.y -= 18
    pdf.text(40, pdf.y, "Itens do Checklist", size=12)
    pdf.y -= 18

    for index, item in enumerate(response.itens.all(), start=1):
        if item.texto_resposta:
            detalhe = item.texto_resposta
        elif item.opcoes_selecionadas:
            opcoes = {str(opcao.id): opcao.valor for opcao in item.pergunta.opcoes.all()}
            detalhe = ", ".join(opcoes.get(str(valor), str(valor)) for valor in item.opcoes_selecionadas)
        else:
            detalhe = "-"
        subitens = [
            trecho.strip(" -")
            for trecho in detalhe.replace("\r", "\n").replace(";", "\n").split("\n")
            for trecho in trecho.split(",")
            if trecho.strip(" -")
        ]
        if not subitens or detalhe == "-":
            subitens = ["Item registrado pelo operador."]

        estimated_lines = 2 + len(subitens) * 2
        pdf.ensure_space(estimated_lines * 13)
        pdf.text(40, pdf.y, f"{index}. {item.pergunta.texto}", size=10)
        pdf.y -= 13
        # pdf.write_paragraph(58, item.pergunta.texto, size=11, max_chars=72, line_height=13)
        pdf.y -= 2
        for subitem in subitens:
            pdf.write_paragraph(58, f"[X] {subitem}", size=10, max_chars=74, line_height=13)
        pdf.y -= 8
        pdf.line(40, pdf.y, 555, pdf.y)
        pdf.y -= 12

    filename = f"checklist-resposta-{response.id}.pdf"
    download = str(request.GET.get('download') or '').strip().lower() in {'1', 'true', 'sim', 'yes'}
    return FileResponse(
        pdf.build(),
        as_attachment=download,
        filename=filename,
        content_type="application/pdf",
    )
