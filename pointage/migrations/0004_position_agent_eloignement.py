from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('employes', '0001_initial'),
        ('sites_rh', '0001_initial'),
        ('pointage', '0003_verrou_appareil'),
    ]

    operations = [
        migrations.CreateModel(
            name='PositionAgent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('longitude', models.DecimalField(decimal_places=7, max_digits=10)),
                ('precision_gps', models.FloatField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('distance_site', models.FloatField(blank=True, help_text='Distance au site en mètres', null=True)),
                ('est_hors_site', models.BooleanField(default=False)),
                ('device_id', models.CharField(blank=True, max_length=200)),
                ('employe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='positions_gps',
                    to='employes.employe',
                )),
                ('site_affecte', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='positions_agents',
                    to='sites_rh.site',
                )),
            ],
            options={
                'verbose_name': 'Position agent',
                'verbose_name_plural': 'Positions agents',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='positionagent',
            index=models.Index(fields=['employe', '-timestamp'], name='pointage_po_employe_idx'),
        ),
        migrations.CreateModel(
            name='EloignementAgent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('debut', models.DateTimeField()),
                ('fin', models.DateTimeField(blank=True, null=True)),
                ('distance_max', models.FloatField(default=0, help_text='Distance max atteinte en mètres')),
                ('est_actif', models.BooleanField(default=True)),
                ('employe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='eloignements',
                    to='employes.employe',
                )),
                ('site', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='eloignements',
                    to='sites_rh.site',
                )),
            ],
            options={
                'verbose_name': 'Éloignement agent',
                'verbose_name_plural': 'Éloignements agents',
                'ordering': ['-debut'],
            },
        ),
    ]
