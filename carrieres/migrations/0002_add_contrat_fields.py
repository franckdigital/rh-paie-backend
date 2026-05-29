from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('carrieres', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='evenementcarriere',
            name='type_contrat',
            field=models.CharField(
                blank=True,
                choices=[('essai', "Période d'essai"), ('CDD', 'CDD'), ('CDI', 'CDI')],
                max_length=10,
                null=True,
                verbose_name='Type de contrat',
            ),
        ),
        migrations.AddField(
            model_name='evenementcarriere',
            name='duree_contrat_mois',
            field=models.IntegerField(
                blank=True, null=True, verbose_name='Durée du contrat (mois)'
            ),
        ),
    ]
