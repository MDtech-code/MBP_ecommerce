"""Settings for the real-Redis integration lane.

Used only by tests marked `redis_integration`, which must exercise a genuine
Redis adapter rather than the local-memory fake in config.test_settings:

    pytest apps/core/tests/test_cache_redis.py --ds=config.test_redis_settings -m redis_integration

CI points TEST_REDIS_URL at DB 15 of a throwaway redis:7 service, so a test
run can never collide with a developer's cache keys (DB 0).
"""

import os

from .test_settings import *  # noqa: F401,F403


_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/15")

CACHES = {
    # L2 — a real Redis server, so adapter behaviour (pickling, add/SET NX,
    # SCAN-based delete_pattern) is the real thing.
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": _REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 300,
    },
    # L1 — still per-process memory, exactly as in production.
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mbp-test-redis-l1",
    },
}

CELERY_BROKER_URL = _REDIS_URL
CELERY_RESULT_BACKEND = _REDIS_URL
