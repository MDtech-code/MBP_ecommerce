"""Test settings — used by pytest locally and by CI.

Rules for this file:
  1. Import everything from `.settings` so a new production requirement can
     never be silently missing here.
  2. Only REPLACE what a test run must not touch: real Redis, real SMTP,
     real password hashing cost, real log files.
  3. Keep the database inherited. The foundation suite is deliberately
     DB-free (it never uses `pytest.mark.django_db`), so pytest-django does
     not create or connect to a database at all. If a future test asks for
     one, pytest-django will fail loudly — that is intended: adding a DB test
     should be a deliberate decision, not an accident.
"""

from .settings import *  # noqa: F401,F403


DEBUG = False


# ── Cache ─────────────────────────────────────────────────────────────────────
# Both levels become local-memory: deterministic, no external service, and no
# key leakage between runs. The real-Redis lane uses config.test_redis_settings.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mbp-test-l2",
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mbp-test-l1",
    },
}


# ── Celery ────────────────────────────────────────────────────────────────────
# Tasks run inline so a test never needs a worker or a broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True


# ── Email ─────────────────────────────────────────────────────────────────────
# Captured in memory instead of being sent through SMTP.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# ── Passwords ─────────────────────────────────────────────────────────────────
# MD5 keeps user-creating tests fast; it has no security meaning in tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# ── Logging ───────────────────────────────────────────────────────────────────
# config/logging.py installs ~19 file handlers. Tests do not need them and the
# files only add noise, so the whole tree is replaced with a null handler.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "WARNING"},
}
