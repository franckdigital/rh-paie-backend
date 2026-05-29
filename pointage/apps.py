from django.apps import AppConfig


class PointageConfig(AppConfig):
    name = 'pointage'

    def ready(self):
        import pointage.signals  # noqa: F401
