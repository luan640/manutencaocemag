# Generated by Django 4.2.15 on 2024-08-21 17:30

from django.db import migrations, models
import datetime

class Migration(migrations.Migration):

    dependencies = [
        ('execucao', '0004_execucao_observacao_execucao_operador_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='execucao',
            name='ultima_atualizacao',
            field=models.DateTimeField(auto_now=True),
            preserve_default=False,
        ),
    ]
