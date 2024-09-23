# Generated by Django 4.2.15 on 2024-08-20 16:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('solicitacao', '0008_alter_solicitacao_maq_parada'),
        ('cadastro', '0003_delete_maquinalocal'),
        ('execucao', '0003_execucao_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='execucao',
            name='observacao',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='execucao',
            name='operador',
            field=models.ManyToManyField(to='cadastro.operador'),
        ),
        migrations.CreateModel(
            name='InfoSolicitacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_manutencao', models.CharField(choices=[('corretiva', 'Corretiva'), ('preditiva', 'Preditiva'), ('preventiva', ' Preventiva'), ('apoio', 'Apoio'), ('projetos', 'Projetos'), ('sesmt', 'SESMT'), ('corretiva_programada', 'Corretiva programada')], max_length=40)),
                ('area_manutencao', models.CharField(choices=[('predial', 'Predial'), ('mecanica', 'Mecânica'), ('eletrica', 'Elétrica')], max_length=20)),
                ('solicitacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='info_solicitacao', to='solicitacao.solicitacao')),
            ],
        ),
    ]
