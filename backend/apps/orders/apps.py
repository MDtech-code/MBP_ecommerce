# apps/orders/apps.py

"""
Orders app configuration.

Registers the app under the apps.orders namespace.
"""

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = "apps.orders"
    verbose_name = "Orders"