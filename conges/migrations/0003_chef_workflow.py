import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conges', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='demandeconge',
            name='chef_approuve_par',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='conges_valides_chef', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='demandeconge',
            name='chef_date_approbation',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='demandeconge',
            name='chef_commentaire',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='demandeconge',
            name='statut',
            field=models.CharField(
                choices=[
                    ('en_attente', 'En attente chef'),
                    ('valide_chef', 'Validé chef — Attente RH'),
                    ('approuve', 'Approuvé RH'),
                    ('refuse', 'Refusé'),
                    ('annule', 'Annulé'),
                ],
                default='en_attente', max_length=20,
            ),
        ),
    ]
