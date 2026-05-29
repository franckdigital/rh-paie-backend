from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paie', '0002_alter_elementsalaire_options_bulletinpaie_cmu_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bulletinpaie',
            name='retard_minutes_total',
            field=models.IntegerField(default=0, help_text='Total minutes de retard sur la période'),
        ),
        migrations.AddField(
            model_name='bulletinpaie',
            name='deduction_retard',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
    ]
