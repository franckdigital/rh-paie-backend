from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carrieres', '0002_add_contrat_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='evenementcarriere',
            name='duree_validite_jours',
            field=models.IntegerField(
                blank=True, null=True,
                verbose_name='Durée de validité (jours)',
                help_text="Durée d'effet de l'événement en jours (suspension, formation, sanction…)",
            ),
        ),
    ]
