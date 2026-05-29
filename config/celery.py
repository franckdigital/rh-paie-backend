import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('rh_paie')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── Tâches planifiées ─────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Marquer les absents tous les jours à 08h30 (heure Abidjan)
    'marquer-absents-quotidien': {
        'task': 'pointage.tasks.marquer_absents_task',
        'schedule': crontab(hour=8, minute=30),
    },
    # Acquérir les congés le 1er de chaque mois à 00h05
    'acquerir-conges-mensuel': {
        'task': 'conges.tasks.acquerir_conges_task',
        'schedule': crontab(day_of_month=1, hour=0, minute=5),
    },
    # Alertes contrats expirant dans 30 jours — chaque lundi à 09h00
    'alertes-contrats-expirants': {
        'task': 'employes.tasks.alertes_contrats_task',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
    },
}

app.conf.timezone = 'Africa/Abidjan'
