from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employes', '0005_add_horaires_applicables_ficheposte'),
        ('entreprises', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='departement',
            name='entreprise',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='departements',
                to='entreprises.entreprise',
            ),
        ),
    ]
