
import os
from urllib.parse import urlparse
from uuid import uuid4

from .test_settings import *  # noqa: F403

TEST_REDIS_INTEGRATION = True
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:56379/15")
_url = urlparse(TEST_REDIS_URL)
if _url.scheme not in {"redis", "rediss"} or not _url.hostname or _url.path != "/15":
    raise ValueError("TEST_REDIS_URL must be an explicit Redis URL using database 15")


TEST_REDIS_KEY_PREFIX = f"test_mbp_{uuid4().hex}"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": TEST_REDIS_URL,
        "KEY_PREFIX": TEST_REDIS_KEY_PREFIX,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 2,
            "SOCKET_TIMEOUT": 2,
            "IGNORE_EXCEPTIONS": False,
        },
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": f"{TEST_REDIS_KEY_PREFIX}_l1",
    },
}

