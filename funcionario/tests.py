from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class FuncionarioAdminTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_superuser(
            matricula='admin',
            nome='Administrador',
            password='123456',
            area='producao',
        )
        self.funcionario = self.user_model.objects.create_user(
            matricula='func001',
            nome='Funcionario Teste',
            password='123456',
            tipo_acesso='solicitante',
        )
        self.client.force_login(self.admin_user)

    def test_admin_change_page_shows_password_reset_link(self):
        change_url = reverse('admin:funcionario_funcionario_change', args=[self.funcionario.pk])
        password_url = reverse('admin:auth_user_password_change', args=[self.funcionario.pk])

        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, password_url)


class FuncionarioManagementViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_user(
            matricula='admin01',
            nome='Administrador',
            password='123456',
            tipo_acesso='administrador',
            area='producao',
        )
        self.client.force_login(self.admin_user)
        self.funcionario = self.user_model.objects.create_user(
            matricula='func002',
            nome='Funcionario Existente',
            password='123456',
            tipo_acesso='solicitante',
        )

    def test_management_page_renders(self):
        response = self.client.get(reverse('gerenciar_funcionarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo solicitante')
        self.assertContains(response, self.funcionario.nome)

    def test_management_page_creates_solicitante_without_password(self):
        response = self.client.post(
            reverse('gerenciar_funcionarios'),
            {
                'action': 'create',
                'matricula': 'func003',
                'nome': 'Novo Funcionario',
                'tipo_acesso': 'solicitante',
                'area': '',
                'telefone': '11999999999',
                'password1': '',
                'password2': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        created = self.user_model.objects.get(matricula='func003')
        self.assertEqual(created.nome, 'Novo Funcionario')
        self.assertEqual(created.tipo_acesso, 'solicitante')
        self.assertEqual(created.area, '')
        self.assertFalse(created.has_usable_password())

    def test_management_page_updates_employee(self):
        response = self.client.post(
            reverse('gerenciar_funcionarios'),
            {
                'action': 'update',
                'funcionario_id': self.funcionario.id,
                'matricula': self.funcionario.matricula,
                'nome': 'Solicitante Alterado',
                'area': 'predial',
                'telefone': '11988887777',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.funcionario.refresh_from_db()
        self.assertEqual(self.funcionario.nome, 'Solicitante Alterado')
        self.assertEqual(self.funcionario.tipo_acesso, 'solicitante')
        self.assertEqual(self.funcionario.area, 'predial')

    def test_management_page_toggles_active_status(self):
        response = self.client.post(
            reverse('gerenciar_funcionarios'),
            {
                'action': 'toggle_status',
                'funcionario_id': self.funcionario.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.funcionario.refresh_from_db()
        self.assertFalse(self.funcionario.is_active)
