try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery non installé — Django fonctionne normalement sans lui
    pass
