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
