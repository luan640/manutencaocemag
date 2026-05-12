import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Importa funcionarios de um CSV com as colunas 'Código' e 'Nome', "
        "criando usuarios solicitantes com senha igual a matricula."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="funcionarios.csv",
            help="Caminho do arquivo CSV. Padrao: funcionarios.csv",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Somente analisa o CSV sem gravar registros no banco.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        dry_run = options["dry_run"]

        if not csv_path.exists():
            raise CommandError(f"Arquivo nao encontrado: {csv_path}")

        with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames or []

            if "Código" not in fieldnames or "Nome" not in fieldnames:
                raise CommandError(
                    "O CSV deve conter as colunas 'Código' e 'Nome'."
                )

            rows = list(reader)

        user_model = get_user_model()
        created = 0
        skipped = 0
        pending_users = []

        for index, row in enumerate(rows, start=2):
            matricula = str(row.get("Código", "")).strip()
            nome = str(row.get("Nome", "")).strip()

            if not matricula or not nome:
                raise CommandError(
                    f"Linha {index} invalida: 'Código' e 'Nome' sao obrigatorios."
                )

            if user_model.objects.filter(matricula=matricula).exists():
                skipped += 1
                continue

            if not dry_run:
                user = user_model(
                    matricula=matricula,
                    nome=nome,
                    tipo_acesso=user_model.SOLICITANTE,
                    area="",
                    telefone="",
                    is_staff=False,
                    is_superuser=False,
                )
                user.set_password(matricula)
                pending_users.append(user)

            created += 1

        if pending_users:
            with transaction.atomic():
                user_model.objects.bulk_create(pending_users, batch_size=200)

        self.stdout.write(
            self.style.SUCCESS(
                f"Importacao concluida. Criados: {created}. Ignorados por matricula existente: {skipped}."
            )
        )
