import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planning', '0001_initial'),
        ('employes', '0005_add_horaires_applicables_ficheposte'),
    ]

    operations = [
        # 1. MembreEquipe model
        migrations.CreateModel(
            name='MembreEquipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_debut', models.DateField(auto_now_add=True)),
                ('est_actif', models.BooleanField(default=True)),
                ('employe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='equipes_appartenues',
                    to='employes.employe',
                )),
                ('equipe', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='membres',
                    to='planning.equipe',
                )),
            ],
            options={
                'verbose_name': "Membre d'équipe",
                'verbose_name_plural': "Membres d'équipe",
                'ordering': ['employe__nom'],
                'unique_together': {('equipe', 'employe')},
            },
        ),
        # 2. Make LignePlanning.planning nullable
        migrations.AlterField(
            model_name='ligneplanning',
            name='planning',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lignes',
                to='planning.planningmensuel',
            ),
        ),
        # 3. Change unique_together
        migrations.AlterUniqueTogether(
            name='ligneplanning',
            unique_together={('employe', 'date')},
        ),
    ]
