# Generated by Django 4.2.15 on 2024-10-24 08:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0017_checklist_itenschecklist'),
        ('solicitacao', '0019_alter_solicitacao_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitacao',
            name='atribuido',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='operador_atribuido', to='cadastro.operador'),
        ),
    ]
