# Generated by Django 4.2.15 on 2024-11-11 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preventiva', '0008_planopreventiva_ativo'),
    ]

    operations = [
        migrations.AddField(
            model_name='planopreventiva',
            name='data_base',
            field=models.DateField(blank=True, null=True),
        ),
    ]
