# Generated by Django 4.2.15 on 2024-11-11 11:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0018_operador_telefone'),
        ('solicitacao', '0023_set_id_initial2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitacao',
            name='setor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cadastro.setor'),
        ),
    ]
