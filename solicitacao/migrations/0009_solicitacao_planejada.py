# Generated by Django 4.2.15 on 2024-08-26 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('solicitacao', '0008_alter_solicitacao_maq_parada'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='planejada',
            field=models.BooleanField(default=False),
        ),
    ]