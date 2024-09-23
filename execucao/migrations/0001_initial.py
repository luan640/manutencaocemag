# Generated by Django 4.2.15 on 2024-08-19 19:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Execucao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('n_execucao', models.IntegerField(blank=True, null=True)),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField()),
                ('che_maq_parada', models.BooleanField(default=False)),
                ('exec_maq_parada', models.BooleanField(default=False)),
                ('apos_exec_maq_parada', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='MaquinaParada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField(blank=True, null=True)),
                ('execucao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='maquina_parada', to='execucao.execucao')),
            ],
        ),
    ]
