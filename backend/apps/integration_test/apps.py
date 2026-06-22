from django.apps import AppConfig


class IntegrationTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.integration_test'

    def ready(self):
        import apps.integration_test.signals