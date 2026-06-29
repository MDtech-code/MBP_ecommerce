from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        import apps.accounts.signals  