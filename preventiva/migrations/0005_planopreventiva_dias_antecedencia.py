# Generated by Django 5.0.1 on 2024-10-16 19:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "preventiva",
            "0004_rename_abertura_automativa_planopreventiva_abertura_automatica",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="planopreventiva",
            name="dias_antecedencia",
            field=models.IntegerField(
                blank=True, help_text="Dias para abertura com antecedência", null=True
            ),
        ),
    ]
