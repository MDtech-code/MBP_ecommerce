"""Real adapter/coordination checks complement (not replace) test_cache.py.

Run explicitly with --ds=config.test_redis_settings. A missing Redis service in
that lane is a failure, not a skip. No application database is required.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache

from apps.core.cache import TwoLevelCache

pytestmark = [
    pytest.mark.redis_integration,
    pytest.mark.skipif(
        not getattr(settings, "TEST_REDIS_INTEGRATION", False),
        reason="Opt-in Redis lane: use --ds=config.test_redis_settings",
    ),
]


class WorkerCache(TwoLevelCache):
    """Independent L1s simulate two workers; both use the real Redis L2."""

    def __init__(self):
        super().__init__()
        self.memory = LocMemCache(f"worker_{uuid4().hex}", {})
        self._lock_retry_interval = 0.01

    @property
    def _l1(self):
        return self.memory


@pytest.mark.parametrize("value", [None, False, 0, [], {"items": [1, 2]}])
def test_redis_roundtrip_backfills_an_independent_l1(value):
    writer, reader = WorkerCache(), WorkerCache()
    writer.set("roundtrip", value)
    assert reader.get("roundtrip") == (value, "l2_redis")
    assert reader.get("roundtrip") == (value, "l1_memory")


def test_invalidation_deletes_matching_l2_keys_but_not_other_prefixes():
    cache = TwoLevelCache()
    cache.set("products:one", 1)
    cache.set("products:two", 2)
    cache.set("cart:one", 3)
    cache.delete("products:")
    assert cache.get("products:one") == (None, "miss")
    assert cache.get("products:two") == (None, "miss")
    # delete clears local L1, so the survivor must really be in Redis.
    assert cache.get("cart:one") == (3, "l2_redis")


def test_namespaced_pattern_cleanup_does_not_flush_other_redis_keys():
    backend = caches["default"]
    raw = backend.client.get_client(write=True)
    sentinel = f"test_mbp_outside_{uuid4().hex}"
    raw.set(sentinel, "preserve", ex=60)
    try:
        backend.set("inside", "remove")
        backend.delete_pattern("*")  # Same namespaced cleanup used by fixtures.
        assert backend.get("inside") is None
        assert raw.get(sentinel) == b"preserve"
    finally:
        raw.delete(sentinel)


def test_redis_atomic_add_allows_only_one_lock_owner():
    first, second = WorkerCache(), WorkerCache()
    ready = Barrier(2)

    def acquire(cache):
        ready.wait(timeout=5)
        return cache._acquire_lock("contended")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(acquire, cache) for cache in (first, second)]
        assert sorted(future.result(timeout=5) for future in futures) == [False, True]
    first._release_lock("contended")
    assert second._acquire_lock("contended") is True
    second._release_lock("contended")


def test_contending_reader_waits_for_builder_then_reads_redis(mocker):
    first, second = WorkerCache(), WorkerCache()
    building, waiting, release = Event(), Event(), Event()
    second_builder = mocker.Mock(return_value="must-not-be-built")
    original_wait = second._wait_for_lock_release

    def observe_wait(key):
        waiting.set()
        return original_wait(key)

    # Observe entry into the losing path, but keep all Redis/lock behavior real.
    mocker.patch.object(second, "_wait_for_lock_release", side_effect=observe_wait)

    def build():
        building.set()
        assert release.wait(timeout=5), "Reader did not reach the lock wait path"
        return {"value": "built-once"}

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(first.get_or_set, "shared", build)
        try:
            assert building.wait(timeout=5)
            reader = pool.submit(second.get_or_set, "shared", second_builder)
            assert waiting.wait(timeout=5)
        finally:
            release.set()
        assert writer.result(timeout=5) == ({"value": "built-once"}, "database")
        assert reader.result(timeout=5) == ({"value": "built-once"}, "l2_redis")
    second_builder.assert_not_called()


def test_failed_builder_releases_real_lock_and_does_not_cache_failure():
    cache = WorkerCache()

    def fail():
        raise RuntimeError("builder failed")

    with pytest.raises(RuntimeError, match="builder failed"):
        cache.get_or_set("failed", fail)
    assert caches["default"].get(cache._lock_key("failed")) is None
    assert cache.get("failed") == (None, "miss")
    assert cache.get_or_set("failed", lambda: "recovered") == ("recovered", "database")
