# Generated by Django 4.2.15 on 2024-08-19 19:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funcionario', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='funcionario',
            name='tipo_acesso',
            field=models.CharField(choices=[('solicitante', 'Solicitante'), ('administrador', 'Administrador')], default='solicitante', max_length=50),
        ),
    ]