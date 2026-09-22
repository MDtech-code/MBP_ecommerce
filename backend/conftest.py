"""Small, shared fixtures. Feature-specific behavior belongs in its own suite."""
import pytest
from django.conf import settings
from django.core.cache import caches
from rest_framework.test import APIClient

# Settings modules are not tests despite the test_ filename prefix.
collect_ignore = ["config/test_settings.py", "config/test_redis_settings.py"]


@pytest.fixture(autouse=True)
def isolated_caches():
    # Fail closed: the old fixture could flush a developer's configured Redis.
    if not getattr(settings, "TESTING", False):
        pytest.fail("Use config.test_settings; application caches must not be cleared")
    redis_lane = getattr(settings, "TEST_REDIS_INTEGRATION", False)
    backends = {alias: caches[alias] for alias in ("default", "local")}
    for alias in backends:
        config = settings.CACHES[alias]
        if redis_lane and alias == "default":
            prefix = getattr(settings, "TEST_REDIS_KEY_PREFIX", "")
            if (
                config["BACKEND"] != "django_redis.cache.RedisCache"
                or not prefix.startswith("test_mbp_")
                or config.get("KEY_PREFIX") != prefix
                or config["LOCATION"] != settings.TEST_REDIS_URL
            ):
                pytest.fail("Redis tests require the isolated namespaced backend")
            # Fail loudly instead of allowing TwoLevelCache's fail-open behavior
            # to make a disconnected Redis integration test falsely pass.
            backends[alias].client.get_client(write=True).ping()
        elif config["BACKEND"] != "django.core.cache.backends.locmem.LocMemCache":
            pytest.fail("Default suite requires isolated local-memory caches")

    def cleanup():
        for alias, backend in backends.items():
            if redis_lane and alias == "default":
                # django-redis applies KEY_PREFIX to this pattern. Never clear()
                # here: RedisCache.clear() would flush the entire database.
                backend.delete_pattern("*")
            else:
                backend.clear()

    cleanup()
    try:
        yield
    finally:
        cleanup()



@pytest.fixture
def api_client():
    return APIClient()
