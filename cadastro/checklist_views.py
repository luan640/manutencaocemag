import json
import logging
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


logger = logging.getLogger(__name__)


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
    PAGE_WIDTH  = 595
    PAGE_HEIGHT = 842
    MARGIN_X    = 40
    CONTENT_W   = 515   # PAGE_WIDTH - 2 * MARGIN_X
    MARGIN_BOT  = 52
    HEADER_H    = 54

    def __init__(self, report_id, generated_at=""):
        self.report_id    = report_id
        self.generated_at = generated_at
        self.pages        = []
        self.current      = []
        self.y            = 0
        self.page_number  = 0
        self._new_page()

    # ── primitives ────────────────────────────────────────────────────────

    def _escape(self, text):
        text = str(text or "")
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return text.encode("cp1252", errors="replace").decode("latin-1")

    def _op(self, cmd):
        self.current.append(cmd)

    def _txt(self, x, y, text, size=10, bold=False):
        f = "/F2" if bold else "/F1"
        self._op(f"BT {f} {size} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm ({self._escape(text)}) Tj ET")

    def _line(self, x1, y1, x2, y2, w=0.5):
        self._op(f"q {w:.2f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S Q")

    def _frect(self, x, y, w, h, r=0.0, g=0.0, b=0.0):
        self._op(f"q {r:.3f} {g:.3f} {b:.3f} rg {x:.1f} {y:.1f} {w:.1f} {h:.1f} re f Q")

    def _srect(self, x, y, w, h, lw=0.5, r=0.7, g=0.7, b=0.7):
        self._op(f"q {lw:.2f} w {r:.2f} {g:.2f} {b:.2f} RG {x:.1f} {y:.1f} {w:.1f} {h:.1f} re S Q")

    def _wrap(self, text, maxc):
        text = str(text or "").strip()
        if not text:
            return [""]
        words = text.split()
        lines, cur = [], words[0]
        for word in words[1:]:
            cand = f"{cur} {word}"
            if len(cand) <= maxc:
                cur = cand
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        return lines

    # ── page lifecycle ─────────────────────────────────────────────────────

    def _new_page(self):
        if self.current:
            self._render_footer()
            self.pages.append("\n".join(self.current))
        self.page_number += 1
        self.current = []
        self._render_header()
        self.y = self.PAGE_HEIGHT - self.HEADER_H - 6

    def _render_header(self):
        # Dark top bar
        self._frect(self.MARGIN_X, self.PAGE_HEIGHT - 44,
                    self.CONTENT_W, 38, r=0.13, g=0.16, b=0.20)
        # White text
        self._op("q 1 1 1 rg")
        self._txt(self.MARGIN_X + 10, self.PAGE_HEIGHT - 22, "CEMAG", size=15, bold=True)
        self._txt(self.MARGIN_X + 10, self.PAGE_HEIGHT - 36, "Gestão de Manutenção", size=7.5)
        self._txt(self.PAGE_WIDTH - 230, self.PAGE_HEIGHT - 24,
                  "Relatório de Manutenção Autônoma", size=9)
        self._op("Q")
        # Blue accent line below bar
        self._frect(self.MARGIN_X, self.PAGE_HEIGHT - 46, self.CONTENT_W, 2,
                    r=0.16, g=0.45, b=0.80)

    def _render_footer(self):
        fy = self.MARGIN_BOT - 4
        self._line(self.MARGIN_X, fy + 8, self.MARGIN_X + self.CONTENT_W, fy + 8, w=0.3)
        self._op("q 0.45 0.45 0.45 rg")
        self._txt(self.MARGIN_X, fy - 4,
                  f"Documento #{self.report_id}   |   Gerado em: {self.generated_at}   |   CEMAG - Gestão de Manutenção",
                  size=7)
        self._txt(self.MARGIN_X + self.CONTENT_W - 55, fy - 4,
                  f"Pag. {self.page_number}", size=7)
        self._op("Q")

    def ensure_space(self, h):
        if self.y - h < self.MARGIN_BOT:
            self._new_page()

    # ── high-level blocks ──────────────────────────────────────────────────

    def title_block(self, main_title, subtitle=""):
        self.ensure_space(58)
        bh = 52
        self._frect(self.MARGIN_X, self.y - bh, self.CONTENT_W, bh,
                    r=0.95, g=0.97, b=1.00)
        self._srect(self.MARGIN_X, self.y - bh, self.CONTENT_W, bh,
                    lw=0.8, r=0.65, g=0.76, b=0.90)
        self._frect(self.MARGIN_X, self.y - bh, 4, bh, r=0.13, g=0.41, b=0.74)
        self._txt(self.MARGIN_X + 14, self.y - 20, main_title, size=14, bold=True)
        if subtitle:
            self._op("q 0.38 0.38 0.38 rg")
            self._txt(self.MARGIN_X + 14, self.y - 36, subtitle, size=9)
            self._op("Q")
        self.y -= bh + 10

    def section_header(self, title):
        self.ensure_space(26)
        self._frect(self.MARGIN_X, self.y - 20, self.CONTENT_W, 20,
                    r=0.20, g=0.24, b=0.29)
        self._op("q 1 1 1 rg")
        self._txt(self.MARGIN_X + 10, self.y - 14, title.upper(), size=8.5, bold=True)
        self._op("Q")
        self.y -= 26

    def info_grid(self, rows):
        col_lbl = 140
        col_val = self.CONTENT_W - col_lbl
        rh = 19
        x = self.MARGIN_X
        for i, (label, value) in enumerate(rows):
            self.ensure_space(rh)
            ry = self.y
            bg = 0.97 if i % 2 == 0 else 1.0
            self._frect(x, ry - rh, self.CONTENT_W, rh, r=bg, g=bg, b=bg)
            self._frect(x, ry - rh, col_lbl, rh, r=0.92, g=0.93, b=0.95)
            self._srect(x, ry - rh, self.CONTENT_W, rh, lw=0.3, r=0.82, g=0.82, b=0.82)
            self._line(x + col_lbl, ry, x + col_lbl, ry - rh, w=0.3)
            self._txt(x + 8, ry - 13, str(label), size=8.5, bold=True)
            val = str(value or "-")
            if len(val) > 62:
                val = val[:60] + "..."
            self._txt(x + col_lbl + 8, ry - 13, val, size=8.5)
            self.y -= rh

    def checklist_item(self, number, question, items):
        """
        items: list of (label, checked)
          checked=True  → realizado   (caixa verde)
          checked=False → não realizado (caixa vermelha)
          checked=None  → resposta de texto livre
        """
        LH = 13  # line height

        # Normaliza e pré-calcula linhas de cada item
        processed = []
        for row in items:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                label, checked = str(row[0]), row[1]
            elif isinstance(row, str):
                label, checked = row, None
            else:
                continue
            max_c = 60 if checked is not None else 68
            lines = self._wrap(label, max_c)
            processed.append((label, checked, lines))

        q_lines = self._wrap(question, 70)
        total_lines = sum(len(lns) for _, _, lns in processed)
        item_h = len(q_lines) * LH + total_lines * LH + 26
        self.ensure_space(item_h)
        iy = self.y
        x  = self.MARGIN_X

        # Fundo alternado
        bg = 0.975 if number % 2 == 0 else 1.0
        self._frect(x, iy - item_h, self.CONTENT_W, item_h, r=bg, g=bg, b=bg)
        ar, ag, ab = (0.13, 0.41, 0.74) if number % 2 == 0 else (0.07, 0.29, 0.55)
        self._frect(x, iy - item_h, 4, item_h, r=ar, g=ag, b=ab)

        # Badge numérico
        self._frect(x + 8, iy - 16, 18, 14, r=0.13, g=0.41, b=0.74)
        self._op("q 1 1 1 rg")
        nx = x + 11 if number < 10 else x + 9
        self._txt(nx, iy - 12, str(number), size=8, bold=True)
        self._op("Q")

        # Pergunta em negrito
        self.y = iy - 13
        for qline in q_lines:
            self._txt(x + 30, self.y, qline, size=9, bold=True)
            self.y -= LH

        self.y -= 5

        # Itens com checkbox e texto completo (sem truncagem)
        for label, checked, lines in processed:
            cy  = self.y
            cx  = x + 30
            bs  = 9

            if checked is None:
                self._op("q 0.22 0.22 0.22 rg")
                for line in lines:
                    self._txt(cx, self.y, line, size=8.5)
                    self.y -= LH
                self._op("Q")
            else:
                # Caixa colorida + ícone vetorial, alinhados ao baseline do texto
                bx = cx
                by = cy - 2   # fundo da caixa ligeiramente abaixo do baseline
                bs = 9        # tamanho da caixa

                if checked:
                    self._frect(bx, by, bs, bs, r=0.08, g=0.56, b=0.20)
                    # Checkmark branco (✓)
                    self._op(
                        f"q 1.4 w 1 1 1 RG "
                        f"{bx+1.5:.1f} {cy+1.5:.1f} m "
                        f"{bx+3.5:.1f} {cy-0.5:.1f} l "
                        f"{bx+7.5:.1f} {cy+5.5:.1f} l S Q"
                    )
                else:
                    self._frect(bx, by, bs, bs, r=0.82, g=0.14, b=0.14)
                    # X branco (✗)
                    self._op(
                        f"q 1.3 w 1 1 1 RG "
                        f"{bx+1.5:.1f} {cy-0.5:.1f} m {bx+7.5:.1f} {cy+5.5:.1f} l S "
                        f"{bx+7.5:.1f} {cy-0.5:.1f} m {bx+1.5:.1f} {cy+5.5:.1f} l S Q"
                    )

                self._op("q 0.08 0.08 0.08 rg" if checked else "q 0.40 0.40 0.40 rg")
                for line in lines:
                    self._txt(cx + 13, self.y, line, size=8.5)
                    self.y -= LH
                self._op("Q")

        self.y -= 4
        self._line(x + 4, self.y, x + self.CONTENT_W, self.y, w=0.25)
        self.y -= 4

    def signature_section(self):
        self.ensure_space(92)
        self.y -= 10
        box_w = (self.CONTENT_W - 16) // 2
        labels = [
            ("Responsável pela Execução", "Operador / Técnico"),
            ("Auditor / Supervisor",      "Gestão de Manutenção"),
        ]
        for i, (label, sub) in enumerate(labels):
            x  = self.MARGIN_X + i * (box_w + 16)
            bh = 74
            self._frect(x, self.y - bh, box_w, bh, r=0.97, g=0.97, b=0.97)
            self._srect(x, self.y - bh, box_w, bh, lw=0.5, r=0.72, g=0.72, b=0.72)
            self._frect(x, self.y - bh, box_w, 16, r=0.22, g=0.25, b=0.29)
            self._op("q 1 1 1 rg")
            self._txt(x + 8, self.y - bh + 5, label, size=7.5, bold=True)
            self._op("Q")
            self._op("q 0.5 0.5 0.5 rg")
            self._txt(x + 8, self.y - bh + 17, sub, size=7)
            self._op("Q")
            self._line(x + 10, self.y - 32, x + box_w - 10, self.y - 32, w=0.6)
            self._txt(x + 10, self.y - 46, "Nome:  _______________________________", size=8)
            self._txt(x + 10, self.y - 60, "Data:  _____ / _____ / _______", size=8)
        self.y -= 86

    # ── build ──────────────────────────────────────────────────────────────

    def build(self):
        if self.current:
            self._render_footer()
            self.pages.append("\n".join(self.current))

        objects = []
        objects.append("<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(self.pages)))
        objects.append(f"<< /Type /Pages /Count {len(self.pages)} /Kids [{kids}] >>")
        f1_id = 3 + len(self.pages) * 2
        f2_id = f1_id + 1

        for index, content in enumerate(self.pages):
            page_id    = 3 + index * 2
            content_id = page_id + 1
            objects.append(
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {f1_id} 0 R /F2 {f2_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            stream = f"q 0.2 w\n{content}\nQ".encode("latin-1")
            objects.append(
                f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream"
            )

        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

        buf = BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(buf.tell())
            buf.write(f"{idx} 0 obj\n{obj}\nendobj\n".encode("latin-1"))
        xref_pos = buf.tell()
        buf.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        buf.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buf.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buf.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF".encode("latin-1")
        )
        buf.seek(0)
        return buf


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
        return timezone.now().date() - timedelta(days=1)
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
        logger.warning('[panorama_autonomas] internal job requested without INTERNAL_JOB_TOKEN configured')
        return JsonResponse({'error': 'INTERNAL_JOB_TOKEN nao configurado.'}, status=503)

    provided_token = _extract_internal_job_token(request)
    if provided_token != configured_token:
        logger.warning('[panorama_autonomas] internal job requested with invalid token')
        return JsonResponse({'error': 'Token invalido.'}, status=403)

    try:
        report_date = _parse_report_date(request.GET.get('date') or request.POST.get('date'))
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    if report_date.weekday() == 6:
        logger.info('[panorama_autonomas] report_date=%s e domingo, envio ignorado.', report_date.isoformat())
        return JsonResponse(
            {'message': 'Data de domingo ignorada. Nenhum envio necessario.', 'report_date': report_date.isoformat(), 'skipped_reason': 'sunday'},
            status=200,
        )

    dry_run = _to_bool(request.GET.get('dry_run') or request.POST.get('dry_run'), default=False)
    result = execute_daily_autonomous_overview(report_date, dry_run=dry_run)
    logger.info(
        '[panorama_autonomas] request complete date=%s dry_run=%s recipients=%s responses=%s missing=%s sent=%s skipped=%s',
        report_date.isoformat(),
        dry_run,
        result['recipient_count'],
        result['response_count'],
        result['missing_count'],
        result['sent_count'],
        result['skipped_reason'],
    )

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
        ChecklistResposta.objects.select_related(
            'formulario', 'versao', 'maquina', 'funcionario'
        ).prefetch_related('itens__pergunta__opcoes'),
        pk=response_id,
    )

    generated_at  = datetime.now().strftime("%d/%m/%Y %H:%M")
    registrado_em = response.criado_em.strftime("%d/%m/%Y %H:%M")

    pdf = SimplePDF(report_id=response.id, generated_at=generated_at)

    # ── Bloco de título ────────────────────────────────────────────────────
    pdf.title_block(
        "Checklist de Manutenção Autônoma",
        (
            f"Registro #{response.id}   |   "
            f"Versão {response.versao.numero}   |   "
            f"{response.data_referencia.strftime('%d/%m/%Y')}"
        ),
    )

    # ── Identificação ──────────────────────────────────────────────────────
    pdf.section_header("Identificação")
    pdf.info_grid([
        ("Formulário",         f"{response.versao.titulo} (v{response.versao.numero})"),
        ("Máquina",            f"{response.maquina.codigo} - {response.maquina.descricao or '-'}"),
        ("Funcionário",        response.funcionario.nome),
        ("Matrícula",          response.funcionario.matricula),
        ("Data de referência", response.data_referencia.strftime("%d/%m/%Y")),
        ("Registrado em",      registrado_em),
        ("Observações",        (response.observacoes or "-")[:120]),
        ("Imagem",             "Anexada" if response.imagem else "Não anexada"),
    ])
    pdf.y -= 8

    # ── Itens do checklist ─────────────────────────────────────────────────
    pdf.section_header("Itens do Checklist")
    for index, item in enumerate(response.itens.all(), start=1):
        pergunta = item.pergunta

        if pergunta.tipo in (
            ChecklistPergunta.TIPO_ESCOLHA_UNICA,
            ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
        ):
            selected_values = set(item.opcoes_selecionadas or [])
            structured = [
                (opcao.valor, opcao.valor in selected_values)
                for opcao in pergunta.opcoes.all()
            ]
        else:
            structured = [(item.texto_resposta or "Sem resposta registrada.", None)]

        pdf.checklist_item(index, pergunta.texto, structured)

    pdf.y -= 12

    filename = f"checklist-resposta-{response.id}.pdf"
    download = str(request.GET.get('download') or '').strip().lower() in {'1', 'true', 'sim', 'yes'}
    return FileResponse(
        pdf.build(),
        as_attachment=download,
        filename=filename,
        content_type="application/pdf",
    )
