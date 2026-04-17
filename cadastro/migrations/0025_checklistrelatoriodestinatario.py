from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0024_alter_checklistresposta_imagem'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChecklistRelatorioDestinatario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('nome_opcional', models.CharField(blank=True, max_length=160, null=True)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ('email',),
            },
        ),
    ]
