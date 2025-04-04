# Generated by Django 4.2.16 on 2025-03-27 13:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cadastro", "0020_tipotarefas_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="maquina",
            name="tipo",
            field=models.CharField(
                blank=True,
                choices=[
                    ("monovia", "Monovia"),
                    ("maquina_de_solda", "Máquina de Solda"),
                    ("robo_kuka", "ROBÔ KUKA"),
                    ("outros", "Outros"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
