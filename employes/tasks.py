from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task(name='employes.tasks.alertes_contrats_task')
def alertes_contrats_task():
    """Tâche Celery hebdomadaire : envoie des alertes pour les contrats expirant dans 30 jours."""
    from employes.models import Employe
    from config.emails import notifier_contrat_expirant

    aujourd_hui = timezone.now().date()
    dans_30j = aujourd_hui + timedelta(days=30)

    expirants = Employe.objects.filter(
        statut='actif',
        date_fin_contrat__isnull=False,
        date_fin_contrat__gte=aujourd_hui,
        date_fin_contrat__lte=dans_30j,
    ).exclude(type_contrat='cdi')

    count = 0
    for employe in expirants:
        jours = (employe.date_fin_contrat - aujourd_hui).days
        notifier_contrat_expirant(employe, jours)
        count += 1

    return f"{count} alerte(s) de contrat envoyée(s)"
