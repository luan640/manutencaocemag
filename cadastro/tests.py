import json
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from cadastro.models import (
    ChecklistFormulario,
    ChecklistFormularioVersao,
    ChecklistPergunta,
    ChecklistPerguntaOpcao,
    ChecklistRelatorioDestinatario,
    ChecklistResposta,
    ChecklistRespostaItem,
    Maquina,
    Setor,
)
from cadastro.services import build_daily_autonomous_overview


def _one_pixel_png():
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\nIDATx\xda\x63\xf8\x0f\x00\x01\x05\x01\x02\x0d\x01\xd5\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class TestChecklistBackend(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_user(
            matricula='9001',
            nome='Admin',
            password='123456',
            tipo_acesso='administrador',
            area='producao',
        )
        self.employee = self.user_model.objects.create_user(
            matricula='9002',
            nome='Funcionario 1',
            password='123456',
            tipo_acesso='operador',
            area='producao',
        )

        self.setor = Setor.objects.create(nome='Setor A')
        self.maquina = Maquina.objects.create(
            codigo='M001',
            descricao='Maquina Principal',
            setor=self.setor,
            area='producao',
            criticidade='a',
        )
        self.maquina_2 = Maquina.objects.create(
            codigo='M002',
            descricao='Maquina Secundaria',
            setor=self.setor,
            area='producao',
            criticidade='b',
        )

        self.client.force_login(self.admin_user)

    def _create_form(self):
        payload = {
            'title': 'Checklist Diario',
            'machine_id': self.maquina.id,
            'questions': [
                {'text': 'Nivel de oleo', 'type': 'single_choice', 'required': True, 'options': ['OK', 'Baixo']},
                {'text': 'Observacao do operador', 'type': 'input', 'required': False},
            ],
        }
        response = self.client.post(
            '/checklists/api/forms/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        return response.json()['form']['id']

    def test_create_form_creates_version_and_questions(self):
        form_id = self._create_form()
        formulario = ChecklistFormulario.objects.get(pk=form_id)
        self.assertIsNotNone(formulario.versao_atual)
        self.assertEqual(formulario.versao_atual.numero, 1)
        self.assertEqual(formulario.versoes.count(), 1)
        self.assertEqual(formulario.versao_atual.perguntas.count(), 2)

    def test_update_form_generates_new_version_without_changing_old_answers_schema(self):
        form_id = self._create_form()
        formulario = ChecklistFormulario.objects.get(pk=form_id)
        versao_1 = formulario.versao_atual
        pergunta_v1 = versao_1.perguntas.order_by('ordem').first()

        update_payload = {
            'title': 'Checklist Diario Atualizado',
            'machine_id': self.maquina_2.id,
            'questions': [
                {
                    'text': 'Nivel de oleo atualizado',
                    'type': 'single_choice',
                    'required': True,
                    'options': ['OK', 'Baixo', 'Vazando'],
                },
                {'text': 'Comentario', 'type': 'input', 'required': False},
            ],
        }

        response = self.client.put(
            f'/checklists/api/forms/{form_id}/',
            data=json.dumps(update_payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        formulario.refresh_from_db()
        self.assertEqual(formulario.versoes.count(), 2)
        self.assertEqual(formulario.versao_atual.numero, 2)
        self.assertEqual(formulario.titulo, 'Checklist Diario Atualizado')
        self.assertEqual(formulario.maquina_id, self.maquina_2.id)
        pergunta_v1.refresh_from_db()
        self.assertEqual(pergunta_v1.texto, 'Nivel de oleo')

    def test_public_submit_requires_image(self):
        form_id = self._create_form()
        formulario = ChecklistFormulario.objects.get(pk=form_id)
        pergunta = formulario.versao_atual.perguntas.order_by('ordem').first()
        opcao = pergunta.opcoes.order_by('ordem').first()

        payload = {
            'funcionario_id': str(self.employee.id),
            'observacoes': 'Sem observacoes',
            'answers': json.dumps({str(pergunta.id): str(opcao.id)}),
        }
        response = self.client.post(
            f'/checklists/api/public/{formulario.token_publico}/submit/',
            data=payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Imagem e obrigatoria', response.json()['error'])

    def test_public_submit_persists_response_with_today_date(self):
        form_id = self._create_form()
        formulario = ChecklistFormulario.objects.get(pk=form_id)
        versao = formulario.versao_atual
        pergunta_1 = versao.perguntas.order_by('ordem').first()
        pergunta_2 = versao.perguntas.order_by('ordem')[1]
        opcao_1 = pergunta_1.opcoes.order_by('ordem').first()

        image_file = SimpleUploadedFile(
            'evidencia.jpg',
            b'fake-image-content',
            content_type='image/jpeg',
        )

        payload = {
            'funcionario_id': str(self.employee.id),
            'observacoes': 'Tudo certo',
            'answers': json.dumps(
                {
                    str(pergunta_1.id): str(opcao_1.id),
                    str(pergunta_2.id): 'Sem anomalias',
                }
            ),
            'imagem': image_file,
        }

        response = self.client.post(
            f'/checklists/api/public/{formulario.token_publico}/submit/',
            data=payload,
        )
        self.assertEqual(response.status_code, 201)

        resposta = ChecklistResposta.objects.get(pk=response.json()['response_id'])
        self.assertEqual(resposta.data_referencia, timezone.now().date())
        self.assertEqual(resposta.itens.count(), 2)

    def test_response_history_can_filter_by_machine(self):
        form_id_1 = self._create_form()
        formulario_1 = ChecklistFormulario.objects.get(pk=form_id_1)
        versao_1 = formulario_1.versao_atual
        pergunta_1 = versao_1.perguntas.order_by('ordem').first()
        opcao_1 = pergunta_1.opcoes.order_by('ordem').first()

        form_2 = ChecklistFormulario.objects.create(
            titulo='Checklist Secundario',
            maquina=self.maquina_2,
            criado_por=self.admin_user,
        )
        versao_2 = ChecklistFormularioVersao.objects.create(
            formulario=form_2,
            numero=1,
            titulo='Checklist Secundario',
            maquina=self.maquina_2,
            criado_por=self.admin_user,
        )
        form_2.versao_atual = versao_2
        form_2.save(update_fields=['versao_atual'])
        pergunta_2 = ChecklistPergunta.objects.create(
            versao=versao_2,
            ordem=1,
            texto='Estado visual',
            tipo=ChecklistPergunta.TIPO_ESCOLHA_UNICA,
            obrigatoria=True,
        )
        opcao_2 = ChecklistPerguntaOpcao.objects.create(pergunta=pergunta_2, valor='OK', ordem=1)
        ChecklistPerguntaOpcao.objects.create(pergunta=pergunta_2, valor='NOK', ordem=2)

        image_1 = SimpleUploadedFile('img1.jpg', b'image-1', content_type='image/jpeg')
        image_2 = SimpleUploadedFile('img2.jpg', b'image-2', content_type='image/jpeg')

        self.client.post(
            f'/checklists/api/public/{formulario_1.token_publico}/submit/',
            data={
                'funcionario_id': str(self.employee.id),
                'answers': json.dumps({str(pergunta_1.id): str(opcao_1.id)}),
                'imagem': image_1,
            },
        )

        self.client.post(
            f'/checklists/api/public/{form_2.token_publico}/submit/',
            data={
                'funcionario_id': str(self.employee.id),
                'answers': json.dumps({str(pergunta_2.id): str(opcao_2.id)}),
                'imagem': image_2,
            },
        )

        history = self.client.get(f'/checklists/api/responses/?maquina_id={self.maquina.id}')
        self.assertEqual(history.status_code, 200)
        responses = history.json()['responses']
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]['machine']['id'], self.maquina.id)


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class TestChecklistDataIntegrity(TestCase):
    def setUp(self):
        self.setor = Setor.objects.create(nome='Integridade')
        self.maquina = Maquina.objects.create(
            codigo='M-INT',
            descricao='Maquina Integridade',
            setor=self.setor,
            area='producao',
            criticidade='b',
        )
        self.funcionario = get_user_model().objects.create_user(
            matricula='6000',
            nome='Tester Integridade',
            password='senha',
            tipo_acesso='operador',
            area='producao',
        )
        self.formulario = ChecklistFormulario.objects.create(
            titulo='Checklist Integridade',
            maquina=self.maquina,
            criado_por=self.funcionario,
        )
        self.versao_inicial = ChecklistFormularioVersao.objects.create(
            formulario=self.formulario,
            numero=1,
            titulo=self.formulario.titulo,
            maquina=self.maquina,
            criado_por=self.funcionario,
        )
        self.formulario.versao_atual = self.versao_inicial
        self.formulario.save(update_fields=['versao_atual'])

        self.pergunta_input = ChecklistPergunta.objects.create(
            versao=self.versao_inicial,
            ordem=1,
            texto='Nivel de oleo',
            tipo=ChecklistPergunta.TIPO_INPUT,
            obrigatoria=True,
        )
        self.pergunta_unica = ChecklistPergunta.objects.create(
            versao=self.versao_inicial,
            ordem=2,
            texto='Maquina limpa',
            tipo=ChecklistPergunta.TIPO_ESCOLHA_UNICA,
            obrigatoria=True,
        )
        self.opcao_sim = ChecklistPerguntaOpcao.objects.create(
            pergunta=self.pergunta_unica, valor='Sim', ordem=1
        )
        self.opcao_nao = ChecklistPerguntaOpcao.objects.create(
            pergunta=self.pergunta_unica, valor='Nao', ordem=2
        )
        self.pergunta_multiplas = ChecklistPergunta.objects.create(
            versao=self.versao_inicial,
            ordem=3,
            texto='Partes checadas',
            tipo=ChecklistPergunta.TIPO_MULTIPLA_ESCOLHA,
            obrigatoria=False,
        )
        self.mult_opcao_a = ChecklistPerguntaOpcao.objects.create(
            pergunta=self.pergunta_multiplas, valor='Correia', ordem=1
        )
        self.mult_opcao_b = ChecklistPerguntaOpcao.objects.create(
            pergunta=self.pergunta_multiplas, valor='Miscelaneas', ordem=2
        )

    def _create_resposta(self, versao=None):
        versao = versao or self.versao_inicial
        imagem = SimpleUploadedFile('imagem.png', _one_pixel_png(), content_type='image/png')
        resposta = ChecklistResposta.objects.create(
            formulario=self.formulario,
            versao=versao,
            maquina=self.maquina,
            funcionario=self.funcionario,
            observacoes='Tudo certo',
            imagem=imagem,
        )
        ChecklistRespostaItem.objects.create(
            resposta=resposta,
            pergunta=self.pergunta_input,
            texto_resposta='Nivel entre limites',
        )
        ChecklistRespostaItem.objects.create(
            resposta=resposta,
            pergunta=self.pergunta_unica,
            opcoes_selecionadas=[self.opcao_sim.pk],
        )
        ChecklistRespostaItem.objects.create(
            resposta=resposta,
            pergunta=self.pergunta_multiplas,
            opcoes_selecionadas=[self.mult_opcao_a.pk, self.mult_opcao_b.pk],
        )
        return resposta

    def test_versioning_keeps_previous_responses(self):
        resposta = self._create_resposta()
        versao_nova = ChecklistFormularioVersao.objects.create(
            formulario=self.formulario,
            numero=2,
            titulo='Checklist Integridade Atualizado',
            maquina=self.maquina,
            criado_por=self.funcionario,
        )
        ChecklistPergunta.objects.create(
            versao=versao_nova,
            ordem=1,
            texto='Nova pergunta',
            tipo=ChecklistPergunta.TIPO_INPUT,
            obrigatoria=False,
        )
        self.formulario.versao_atual = versao_nova
        self.formulario.save(update_fields=['versao_atual'])

        resposta.refresh_from_db()
        self.assertEqual(resposta.versao.numero, 1)
        self.assertEqual(
            resposta.itens.get(pergunta=self.pergunta_input).texto_resposta,
            'Nivel entre limites',
        )
        self.assertEqual(self.formulario.versoes.count(), 2)

    def test_response_items_and_machine_history(self):
        resposta = self._create_resposta()
        itens = resposta.itens.all()
        self.assertEqual(itens.count(), 3)
        texto = itens.get(pergunta=self.pergunta_input)
        self.assertEqual(texto.texto_resposta, 'Nivel entre limites')
        unica = itens.get(pergunta=self.pergunta_unica)
        self.assertEqual(unica.opcoes_selecionadas, [self.opcao_sim.pk])
        multiplas = itens.get(pergunta=self.pergunta_multiplas)
        self.assertListEqual(
            multiplas.opcoes_selecionadas,
            [self.mult_opcao_a.pk, self.mult_opcao_b.pk],
        )
        historico = ChecklistResposta.objects.filter(maquina=self.maquina)
        self.assertEqual(historico.count(), 1)

    def test_default_metadata_and_public_token(self):
        resposta = self._create_resposta()
        self.assertEqual(resposta.data_referencia, timezone.now().date())
        self.assertEqual(resposta.observacoes, 'Tudo certo')
        self.assertIsNotNone(self.formulario.token_publico)
        self.assertTrue(
            ChecklistFormulario.objects.filter(token_publico=self.formulario.token_publico).exists()
        )


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class TestChecklistReportRecipients(TestCase):
    def setUp(self):
        self.client = Client()
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            matricula='9100',
            nome='Admin Relatorio',
            password='123456',
            tipo_acesso='administrador',
            area='producao',
        )
        self.operator_user = user_model.objects.create_user(
            matricula='9101',
            nome='Operador Relatorio',
            password='123456',
            tipo_acesso='operador',
            area='producao',
        )
        self.requester_user = user_model.objects.create_user(
            matricula='9102',
            nome='Solicitante Relatorio',
            password='123456',
            tipo_acesso='solicitante',
            area='producao',
        )

    def test_duplicate_emails_are_not_allowed(self):
        ChecklistRelatorioDestinatario.objects.create(email='teste@empresa.com')
        self.client.force_login(self.admin_user)
        response = self.client.post(
            '/checklists/api/report-recipients/',
            data=json.dumps({'email': 'teste@empresa.com', 'name': 'Duplicado'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Ja existe', response.json()['error'])

    def test_report_recipient_status_can_toggle(self):
        recipient = ChecklistRelatorioDestinatario.objects.create(email='ativo@empresa.com', ativo=True)
        self.client.force_login(self.admin_user)
        response = self.client.patch(
            f'/checklists/api/report-recipients/{recipient.id}/',
            data=json.dumps({'action': 'inactivate'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        recipient.refresh_from_db()
        self.assertFalse(recipient.ativo)

    def test_only_admin_or_staff_can_access_report_recipient_screen(self):
        self.client.force_login(self.admin_user)
        admin_response = self.client.get('/checklists/destinatarios/')
        self.assertEqual(admin_response.status_code, 200)

        self.client.force_login(self.operator_user)
        operator_response = self.client.get('/checklists/destinatarios/')
        self.assertEqual(operator_response.status_code, 404)

        self.client.force_login(self.requester_user)
        requester_response = self.client.get('/checklists/destinatarios/')
        self.assertEqual(requester_response.status_code, 404)


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.FileSystemStorage",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='robot@empresa.com',
    INTERNAL_JOB_TOKEN='secret-job-token',
)
class TestChecklistDailyOverview(TestCase):
    def setUp(self):
        self.client = Client()
        user_model = get_user_model()
        self.funcionario = user_model.objects.create_user(
            matricula='9200',
            nome='Funcionario Relatorio',
            password='123456',
            tipo_acesso='operador',
            area='producao',
        )
        self.admin_user = user_model.objects.create_user(
            matricula='9201',
            nome='Admin Relatorio',
            password='123456',
            tipo_acesso='administrador',
            area='producao',
        )
        self.setor = Setor.objects.create(nome='Setor Relatorio')
        self.maquina = Maquina.objects.create(
            codigo='MR-01',
            descricao='Maquina Relatorio',
            setor=self.setor,
            area='producao',
            criticidade='a',
        )
        self.formulario = ChecklistFormulario.objects.create(
            titulo='Autonoma Diario',
            maquina=self.maquina,
            criado_por=self.admin_user,
        )
        self.versao = ChecklistFormularioVersao.objects.create(
            formulario=self.formulario,
            numero=1,
            titulo='Autonoma Diario',
            maquina=self.maquina,
            criado_por=self.admin_user,
        )
        self.formulario.versao_atual = self.versao
        self.formulario.save(update_fields=['versao_atual'])
        self.maquina_2 = Maquina.objects.create(
            codigo='MR-02',
            descricao='Maquina Pendente',
            setor=self.setor,
            area='producao',
            criticidade='b',
        )
        self.formulario_pendente = ChecklistFormulario.objects.create(
            titulo='Autonoma Pendente',
            maquina=self.maquina_2,
            criado_por=self.admin_user,
        )
        self.versao_pendente = ChecklistFormularioVersao.objects.create(
            formulario=self.formulario_pendente,
            numero=1,
            titulo='Autonoma Pendente',
            maquina=self.maquina_2,
            criado_por=self.admin_user,
        )
        self.formulario_pendente.versao_atual = self.versao_pendente
        self.formulario_pendente.save(update_fields=['versao_atual'])

    def _create_response(self, report_date, created_at=None):
        image = SimpleUploadedFile('img.png', _one_pixel_png(), content_type='image/png')
        response = ChecklistResposta.objects.create(
            formulario=self.formulario,
            versao=self.versao,
            maquina=self.maquina,
            funcionario=self.funcionario,
            data_referencia=report_date,
            imagem=image,
        )
        if created_at is not None:
            ChecklistResposta.objects.filter(pk=response.pk).update(criado_em=created_at)
            response.refresh_from_db()
        return response

    def test_build_overview_returns_rows_for_selected_day(self):
        today = timezone.now().date()
        now = timezone.now().replace(hour=10, minute=15, second=0, microsecond=0)
        self._create_response(today, created_at=now)
        self._create_response(today - timedelta(days=1))

        overview = build_daily_autonomous_overview(today)

        self.assertEqual(overview['response_count'], 1)
        self.assertEqual(overview['context']['rows'][0]['autonomous_name'], 'Autonoma Diario')
        self.assertEqual(overview['context']['rows'][0]['employee_name'], 'Funcionario Relatorio')
        self.assertEqual(overview['context']['rows'][0]['created_at'], now)
        self.assertTrue(overview['context']['has_missing_rows'])
        self.assertEqual(overview['context']['missing_count'], 1)
        self.assertEqual(overview['context']['missing_rows'][0]['autonomous_name'], 'Autonoma Pendente')

    def test_build_overview_returns_empty_state_when_no_responses(self):
        overview = build_daily_autonomous_overview(timezone.now().date())
        self.assertEqual(overview['response_count'], 0)
        self.assertFalse(overview['context']['has_rows'])
        self.assertEqual(overview['context']['rows'], [])
        self.assertTrue(overview['context']['has_missing_rows'])
        self.assertEqual(overview['context']['missing_count'], 2)

    def test_command_does_not_send_without_active_recipients(self):
        output = StringIO()
        call_command('enviar_panorama_autonomas', stdout=output)
        self.assertEqual(len(getattr(mail, 'outbox', [])), 0)
        self.assertIn('Nenhum destinatario ativo configurado', output.getvalue())

    def test_command_defaults_to_previous_day_when_date_is_omitted(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        ChecklistRelatorioDestinatario.objects.create(email='ontem@empresa.com')

        call_command('enviar_panorama_autonomas')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(yesterday.strftime('%d/%m/%Y'), mail.outbox[0].subject)

    def test_command_sends_email_with_responses(self):
        report_date = timezone.now().date()
        created_at = timezone.now().replace(hour=22, minute=45, second=0, microsecond=0)
        self._create_response(report_date, created_at=created_at)
        ChecklistRelatorioDestinatario.objects.create(email='um@empresa.com')
        ChecklistRelatorioDestinatario.objects.create(email='dois@empresa.com')

        call_command('enviar_panorama_autonomas', report_date=report_date.isoformat())

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Panorama de respostas das autônomas', message.subject)
        self.assertEqual(sorted(message.to), ['dois@empresa.com', 'um@empresa.com'])
        self.assertIn('Autonoma Diario', message.body)
        self.assertIn('Funcionario Relatorio', message.body)
        self.assertIn('Autonomas nao realizadas', message.body)
        self.assertIn('Autonoma Pendente', message.body)

    def test_command_sends_empty_state_email_when_no_responses(self):
        report_date = timezone.now().date()
        ChecklistRelatorioDestinatario.objects.create(email='vazio@empresa.com')

        call_command('enviar_panorama_autonomas', report_date=report_date.isoformat())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Não teve respostas', mail.outbox[0].body)

    def test_command_dry_run_does_not_send(self):
        report_date = timezone.now().date()
        ChecklistRelatorioDestinatario.objects.create(email='teste@empresa.com')
        output = StringIO()

        call_command('enviar_panorama_autonomas', report_date=report_date.isoformat(), dry_run=True, stdout=output)

        self.assertEqual(len(getattr(mail, 'outbox', [])), 0)
        self.assertIn('Dry-run concluido sem envio de e-mail.', output.getvalue())

    def test_internal_job_url_requires_valid_token(self):
        response = self.client.get('/internal/jobs/enviar-panorama-autonomas/')
        self.assertEqual(response.status_code, 403)

    def test_internal_job_url_executes_dry_run(self):
        report_date = timezone.now().date()
        ChecklistRelatorioDestinatario.objects.create(email='teste@empresa.com')

        response = self.client.get(
            '/internal/jobs/enviar-panorama-autonomas/',
            {'token': 'secret-job-token', 'date': report_date.isoformat(), 'dry_run': 'true'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['report_date'], report_date.isoformat())
        self.assertTrue(data['dry_run'])
        self.assertEqual(data['recipient_count'], 1)

    def test_internal_job_url_defaults_to_previous_day_when_date_is_omitted(self):
        yesterday = timezone.now().date() - timedelta(days=1)
        ChecklistRelatorioDestinatario.objects.create(email='teste@empresa.com')

        response = self.client.get(
            '/internal/jobs/enviar-panorama-autonomas/',
            {'token': 'secret-job-token', 'dry_run': 'true'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['report_date'], yesterday.isoformat())
        self.assertTrue(data['dry_run'])
