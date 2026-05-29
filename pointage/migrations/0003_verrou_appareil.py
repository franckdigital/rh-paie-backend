from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employes', '0001_initial'),
        ('pointage', '0002_pointage_correction_par_pointage_datetime_correction_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='VerrouAppareil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(max_length=200, unique=True, verbose_name='ID appareil')),
                ('locked_at', models.DateTimeField(verbose_name='Verrouillé le')),
                ('employe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='verrous_appareils',
                    to='employes.employe',
                    verbose_name='Propriétaire',
                )),
            ],
            options={
                'verbose_name': 'Verrou appareil',
                'verbose_name_plural': 'Verrous appareils',
                'ordering': ['-locked_at'],
            },
        ),
    ]
