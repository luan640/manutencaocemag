# Generated by Django 4.2.15 on 2024-10-24 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastro', '0017_checklist_itenschecklist'),
    ]

    operations = [
        migrations.AddField(
            model_name='operador',
            name='telefone',
            field=models.CharField(blank=True, max_length=13, null=True),
        ),
    ]