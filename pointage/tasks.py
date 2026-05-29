from celery import shared_task
from django.core.management import call_command


@shared_task(name='pointage.tasks.marquer_absents_task', bind=True, max_retries=3)
def marquer_absents_task(self):
    """Tâche Celery quotidienne : marque les absents du jour."""
    try:
        call_command('marquer_absents')
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)
