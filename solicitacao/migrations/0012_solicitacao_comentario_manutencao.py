# Generated by Django 4.2.15 on 2024-09-11 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitacao', '0011_solicitacao_tarefa'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='comentario_manutencao',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
    ]
