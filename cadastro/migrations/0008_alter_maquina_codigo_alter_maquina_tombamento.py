# Generated by Django 4.2.15 on 2024-08-23 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0007_alter_maquina_tombamento_maquina_unique_maquina'),
    ]

    operations = [
        migrations.AlterField(
            model_name='maquina',
            name='codigo',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterField(
            model_name='maquina',
            name='tombamento',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]