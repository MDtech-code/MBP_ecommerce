from django.apps import AppConfig


class IntegrationTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'integration_test'

    def ready(self):
        import integration_test.signals