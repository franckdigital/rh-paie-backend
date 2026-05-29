from django.apps import AppConfig


class PlanningConfig(AppConfig):
    name = 'planning'

    def ready(self):
        import planning.signals  # noqa
