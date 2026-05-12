from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class ImportarFuncionariosCsvCommandTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_importa_novos_funcionarios_e_pula_matriculas_existentes(self):
        self.user_model.objects.create_user(
            matricula="1001",
            nome="Ja Existe",
            password="senha-antiga",
            tipo_acesso="operador",
            area="producao",
        )

        csv_path = Path("test_funcionarios.csv")
        csv_path.write_text(
            "Código,Nome\n1001,Usuario Existente\n1002,Novo Usuario\n",
            encoding="utf-8-sig",
        )

        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        call_command("importar_funcionarios_csv", str(csv_path))

        existente = self.user_model.objects.get(matricula="1001")
        novo = self.user_model.objects.get(matricula="1002")

        self.assertEqual(existente.tipo_acesso, "operador")
        self.assertTrue(existente.check_password("senha-antiga"))

        self.assertEqual(novo.nome, "Novo Usuario")
        self.assertEqual(novo.tipo_acesso, "solicitante")
        self.assertEqual(novo.area, "")
        self.assertEqual(novo.telefone, "")
        self.assertTrue(novo.check_password("1002"))

    def test_dry_run_nao_persiste_registros(self):
        csv_path = Path("test_funcionarios_dry_run.csv")
        csv_path.write_text(
            "Código,Nome\n2001,Usuario Dry Run\n",
            encoding="utf-8-sig",
        )

        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        call_command("importar_funcionarios_csv", str(csv_path), "--dry-run")

        self.assertFalse(self.user_model.objects.filter(matricula="2001").exists())
