from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites_rh', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='pays',
            field=models.CharField(blank=True, max_length=100, verbose_name='Pays'),
        ),
    ]
