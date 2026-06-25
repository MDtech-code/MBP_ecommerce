from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'

    def ready(self):
        # Register monitoring backends after apps are loaded
        import sentry_sdk
        from django.conf import settings
        from apps.core.api.exceptions import register_monitor

        if getattr(settings, 'SENTRY_DSN', ''):
            register_monitor(sentry_sdk.capture_exception)