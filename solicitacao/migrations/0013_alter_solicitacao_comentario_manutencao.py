# Generated by Django 4.2.15 on 2024-09-19 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitacao', '0012_solicitacao_comentario_manutencao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitacao',
            name='comentario_manutencao',
            field=models.TextField(blank=True, null=True),
        ),
    ]
