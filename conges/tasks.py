from celery import shared_task
from django.core.management import call_command


@shared_task(name='conges.tasks.acquerir_conges_task', bind=True, max_retries=3)
def acquerir_conges_task(self):
    """Tâche Celery mensuelle : attribue 2.5j de congés payés à tous les employés actifs."""
    try:
        call_command('acquerir_conges')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 10)
