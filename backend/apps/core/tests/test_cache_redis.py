"""Real-Redis integration lane for TwoLevelCache.

Every claim in apps/core/cache.py — sentinel encoding, L1→L2 fallback with
backfill, SCAN-based invalidation, single-flight rebuild — is only true
against a genuine Redis server. Against LocMem the assertions would pass for
the wrong reason, so this module refuses to run unless the configured default
cache really is django_redis.

    # CI / local, against Redis DB 15:
    pytest apps/core/tests/test_cache_redis.py --ds=config.test_redis_settings -m redis_integration

Collected by a plain `pytest` run too, but skipped there, because
config.test_settings points both cache levels at local memory.
"""

import pytest
from django.core.cache import caches
from django_redis.cache import RedisCache

from apps.core.cache import TwoLevelCache

pytestmark = pytest.mark.redis_integration


if not isinstance(caches["default"], RedisCache):
    pytest.skip(
        "requires config.test_redis_settings and a live Redis (DB 15)",
        allow_module_level=True,
    )


# Namespace so this module can never touch a developer's real keys.
PREFIX = "ci:two-level-cache"


def _versioned(key: str) -> str:
    return f"v{TwoLevelCache.CACHE_VERSION}:{key}"


@pytest.fixture()
def cache():
    instance = TwoLevelCache(l1_timeout=30, l2_timeout=30)
    yield instance
    # Clean up both levels whatever the test did.
    try:
        caches["default"].delete_pattern(f"*{PREFIX}*")
    except Exception:  # pragma: no cover - cleanup must never mask a result
        pass
    caches["local"].clear()


# ─── The lane is real ─────────────────────────────────────────────────────────

def test_l2_is_a_real_redis_backend():
    """Fails loudly if someone runs this lane against the LocMem fake."""
    assert isinstance(caches["default"], RedisCache)


# ─── Set / get across both levels ─────────────────────────────────────────────

def test_set_writes_the_sentinel_encoded_value_to_both_levels(cache):
    key = f"{PREFIX}:both"
    cache.set(key, {"id": 1, "name": "Brake Pad"})

    # Read the backends directly: versioned key, {"__v": ...} sentinel wrapper.
    expected = {"__v": {"id": 1, "name": "Brake Pad"}}
    assert caches["local"].get(_versioned(key)) == expected
    assert caches["default"].get(_versioned(key)) == expected


def test_get_serves_from_memory_after_set(cache):
    key = f"{PREFIX}:l1"
    cache.set(key, "value")
    assert cache.get(key) == ("value", "l1_memory")


def test_get_falls_back_to_redis_and_backfills_memory(cache):
    key = f"{PREFIX}:l2"
    cache.set(key, [1, 2, 3])
    caches["local"].clear()

    assert cache.get(key) == ([1, 2, 3], "l2_redis")
    # The L2 hit must repopulate L1 for the next request.
    assert caches["local"].get(_versioned(key)) == {"__v": [1, 2, 3]}


@pytest.mark.parametrize("falsy", [[], {}, False, 0, "", None])
def test_falsy_values_are_not_mistaken_for_a_miss(cache, falsy):
    """The documented reason the {"__v": ...} sentinel exists."""
    key = f"{PREFIX}:falsy:{type(falsy).__name__}"
    cache.set(key, falsy)

    value, source = cache.get(key)
    assert source != "miss"
    assert value == falsy


def test_delete_removes_the_key_from_both_levels(cache):
    key = f"{PREFIX}:delete"
    cache.set(key, "value")

    cache.delete(key)

    assert cache.get(key) == (None, "miss")
    assert caches["default"].get(_versioned(key)) is None


# ─── Cache-aside with stampede protection ────────────────────────────────────

def test_get_or_set_builds_from_database_only_on_miss(cache):
    key = f"{PREFIX}:builder"
    calls: list[int] = []

    def builder():
        calls.append(1)
        return {"built": True}

    assert cache.get_or_set(key, builder) == ({"built": True}, "database")
    assert cache.get_or_set(key, builder) == ({"built": True}, "l1_memory")
    assert len(calls) == 1


def test_get_or_set_releases_the_lock_and_propagates_builder_errors(cache):
    """A failed rebuild must re-raise AND leave no lock behind."""
    key = f"{PREFIX}:builder-error"

    def boom():
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError):
        cache.get_or_set(key, boom)

    assert caches["default"].get(f"lock:{_versioned(key)}") is None
