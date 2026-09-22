"""Isolated pytest settings. Never read application .env or use its services.

PostgreSQL settings are opt-in via TEST_POSTGRES_* (see docs/testing.md).
Production password validators, middleware and installed apps stay intact.
"""
import os
from unittest.mock import patch

# Base settings require these values even for tests that never touch a DB.
# Override during import, rather than let a developer's shell/.env select services.
_test_env = {
    "SECRET_KEY": "test-only-not-a-production-secret-key-mbp",
    "DEBUG": "False",
    "SENTRY_DSN": "",
    "POSTGRES_DB": "mbp_tests",
    "POSTGRES_USER": "mbp_tests",
    "POSTGRES_PASSWORD": "test-only",
    "POSTGRES_HOST": "127.0.0.1",
    # Import-only defaults. Final DATABASES below reads TEST_POSTGRES_PORT:
    # local compose=55432, CI explicitly supplies 5432.
    "POSTGRES_PORT": "55432",
    # Deliberately unusable import-only sentinel, NOT a live Redis endpoint.
    # CACHES and Celery are replaced below; the real-Redis lane uses
    # config.test_redis_settings and its separate TEST_REDIS_URL.
    "REDIS_URL": "redis://127.0.0.1:1/15",
    "GOOGLE_CLIENT_ID": "test-client",
    "GOOGLE_CLIENT_SECRET": "test-secret",
    "GOOGLE_REDIRECT_URI": "https://testserver/callback",
    "FACEBOOK_APP_ID": "test-app",
    "FACEBOOK_APP_SECRET": "test-secret",
}
with patch.dict(os.environ, _test_env), patch("environ.Env.read_env"):
    from .settings import *  # noqa: F403

TESTING = True
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
_db_name = os.environ.get("TEST_POSTGRES_DB", "test_mbp_ecommerce")
if not _db_name.startswith("test_mbp_"):
    raise ValueError("TEST_POSTGRES_DB must start with test_mbp_ for safety")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mbp_tests",
        "USER": os.environ.get("TEST_POSTGRES_USER", "mbp_tests"),
        "PASSWORD": os.environ.get("TEST_POSTGRES_PASSWORD", "test-only"),
        "HOST": os.environ.get("TEST_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("TEST_POSTGRES_PORT", "55432"),
        "TEST": {"NAME": _db_name},
    }
}
CACHES = {
    name: {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": f"mbp-tests-{name}",
    }
    for name in ("default", "local")
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@example.test"
FRONTEND_URL = "https://shop.example.test"
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
# .delay() publishes to memory://; without a worker it does not run the task.
# Service tests must mock dispatch and assert its arguments. Task tests call
# .run()/.apply(); workflow tests opt into eager execution explicitly. Eager
# execution still does not prove delivery through a real broker/worker.
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Let pytest capture logs; no application log files or remote monitoring.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {},
    "root": {"handlers": [], "level": "WARNING"},
}
