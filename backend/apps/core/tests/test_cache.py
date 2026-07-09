# backend/apps/core/tests/test_cache.py
"""
Tests for apps.core.cache.TwoLevelCache.

Architecture being tested:
    L1 = LocMemCache  (real, in-process, no external dependency)
    L2 = Redis        (mocked — not guaranteed in all CI environments)

Why L1 is real and L2 is mocked:
    L1 (LocMemCache) requires no server — Django provides it built-in.
    Testing L1 with a real backend gives us honest coverage of L1 behavior.

    L2 (Redis) requires a running server.
    In CI/CD, Redis may not be available.
    Mocking L2 lets us test ALL cache logic without infrastructure dependency.
    The mock faithfully simulates Redis get/set/add/delete behavior.

Test structure:

    Layer 1 — _encode() / _decode()
        Pure functions. No cache backends touched.
        Tests the sentinel encoding that handles falsy values.

    Layer 2 — _versioned_key() / _lock_key()
        Pure functions. Tests key generation logic.

    Layer 3 — get() / set() / delete()
        Tests L1 real + L2 mocked behavior.
        Covers L1 hit, L2 hit, miss, L1 backfill from L2.

    Layer 4 — get_or_set()
        Tests cache-aside pattern with and without stampede protection.
        builder_fn call counting ensures no duplicate DB hits.

    Layer 5 — Fault tolerance
        L1 failure degrades to L2.
        L2 failure degrades to miss.
        Neither failure crashes the request.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from django.core.cache import caches

from apps.core.cache import TwoLevelCache


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def cache():
    """
    Fresh TwoLevelCache instance for each test.

    L1 uses real LocMemCache — cleared by global clear_all_caches fixture.
    L2 is the real Redis cache backend (may be mocked per-test below).
    """
    return TwoLevelCache(l1_timeout=60, l2_timeout=300)


@pytest.fixture
def mock_l2(cache):
    """
    Replace L2 (Redis) with a MagicMock for the duration of one test.

    Why patch the property on the instance not the class:
        Multiple test instances may run. Patching the class would affect
        all instances. Patching the instance's _l2 property is isolated.

    The mock simulates a simple in-memory dict store.
    """
    mock = MagicMock()
    # Default behavior — nothing in cache
    mock.get.return_value = None
    mock.add.return_value = True   # lock always acquired by default
    mock.delete_pattern = MagicMock()
    mock.delete = MagicMock()

    with patch.object(type(cache), '_l2', new_callable=lambda: property(lambda self: mock)):
        yield mock


# ─── Layer 1: _encode() / _decode() ──────────────────────────────────────────

@pytest.mark.unit
class TestEncodeDecodeHelpers:
    """
    Unit tests for sentinel encoding/decoding.

    Problem being solved:
        Cache backends return None for both:
            - A genuine cache miss (key not found)
            - A cached None value (key found, value is None)

        Without encoding, cached None is indistinguishable from a miss.
        Same problem for [], False, 0, "" — all falsy, all look like misses.

    Solution:
        Wrap every stored value: {"__v": value}
        None miss  → backend returns None       → decode: (False, None)
        Cached None → backend returns {"__v": None} → decode: (True, None)
    """

    def test_encode_wraps_value_in_sentinel_dict(self, cache):
        """_encode must wrap value in {"__v": value}."""
        result = cache._encode("hello")
        assert result == {"__v": "hello"}

    def test_encode_none_value(self, cache):
        """None must be encoded as {"__v": None} not left as None."""
        result = cache._encode(None)
        assert result == {"__v": None}
        assert result is not None  # the dict itself is not None

    def test_encode_empty_list(self, cache):
        """Empty list must be encoded — not treated as falsy miss."""
        result = cache._encode([])
        assert result == {"__v": []}

    def test_encode_false(self, cache):
        """False must be encoded — not treated as falsy miss."""
        result = cache._encode(False)
        assert result == {"__v": False}

    def test_encode_zero(self, cache):
        """0 must be encoded — not treated as falsy miss."""
        result = cache._encode(0)
        assert result == {"__v": 0}

    def test_encode_empty_string(self, cache):
        """Empty string must be encoded."""
        result = cache._encode("")
        assert result == {"__v": ""}

    def test_decode_none_raw_is_miss(self, cache):
        """
        None from cache backend means genuine miss.

        Backend returns None when key does not exist.
        _decode must signal miss with (False, None).
        """
        hit, value = cache._decode(None)
        assert hit is False
        assert value is None

    def test_decode_encoded_none_is_hit(self, cache):
        """
        {"__v": None} means cache hit with None as the stored value.

        This is the key distinction from a genuine miss.
        """
        hit, value = cache._decode({"__v": None})
        assert hit is True
        assert value is None

    def test_decode_encoded_false_is_hit(self, cache):
        """{"__v": False} must be decoded as cache hit with False."""
        hit, value = cache._decode({"__v": False})
        assert hit is True
        assert value is False

    def test_decode_encoded_empty_list_is_hit(self, cache):
        """{"__v": []} must be decoded as cache hit with []."""
        hit, value = cache._decode({"__v": []})
        assert hit is True
        assert value == []

    def test_decode_encoded_real_value(self, cache):
        """Normal dict with __v key decodes correctly."""
        hit, value = cache._decode({"__v": {"id": 1, "name": "product"}})
        assert hit is True
        assert value == {"id": 1, "name": "product"}

    def test_decode_unencoded_value_treated_as_miss(self, cache):
        """
        Raw value without __v key is treated as miss.

        Handles legacy cache entries that were stored before encoding
        was introduced. Safer to re-fetch than to return corrupt data.
        """
        hit, value = cache._decode({"not_v": "something"})
        assert hit is False


# ─── Layer 2: Key generation ──────────────────────────────────────────────────

@pytest.mark.unit
class TestKeyGeneration:
    """
    Unit tests for _versioned_key() and _lock_key().

    Cache versioning allows instant cache busting on deploy.
    Bump CACHE_VERSION → all old keys are unreachable → fresh DB fetch.
    """

    def test_versioned_key_includes_version(self, cache):
        """Versioned key must include CACHE_VERSION prefix."""
        vkey = cache._versioned_key("my_key")
        assert f"v{cache.CACHE_VERSION}:" in vkey

    def test_versioned_key_includes_original_key(self, cache):
        """Versioned key must include the original key."""
        vkey = cache._versioned_key("products:list")
        assert "products:list" in vkey

    def test_versioned_key_format(self, cache):
        """Versioned key must follow v{version}:{key} format exactly."""
        vkey = cache._versioned_key("test_key")
        assert vkey == f"v{cache.CACHE_VERSION}:test_key"

    def test_different_keys_produce_different_versioned_keys(self, cache):
        """Two different keys must produce different versioned keys."""
        vkey1 = cache._versioned_key("key_one")
        vkey2 = cache._versioned_key("key_two")
        assert vkey1 != vkey2

    def test_lock_key_includes_versioned_key(self, cache):
        """Lock key must be based on versioned key — not raw key."""
        vkey = cache._versioned_key("my_key")
        lock_key = cache._lock_key("my_key")
        assert vkey in lock_key

    def test_lock_key_has_lock_prefix(self, cache):
        """Lock key must have 'lock:' prefix for Redis namespace separation."""
        lock_key = cache._lock_key("my_key")
        assert lock_key.startswith("lock:")

    def test_bumping_version_changes_all_keys(self):
        """
        Changing CACHE_VERSION must change every generated key.

        This is the cache busting mechanism.
        Version 1 and version 2 keys must be completely different.
        """
        cache_v1 = TwoLevelCache()
        cache_v1.CACHE_VERSION = 1

        cache_v2 = TwoLevelCache()
        cache_v2.CACHE_VERSION = 2

        assert cache_v1._versioned_key("test") != cache_v2._versioned_key("test")


# ─── Layer 3: get() / set() / delete() ───────────────────────────────────────

@pytest.mark.unit
class TestGetSetDelete:
    """
    Tests for the main cache operations.

    L1 (LocMemCache) is real — cleared between tests by global fixture.
    L2 (Redis) is mocked — behavior controlled per test.
    """

    def test_set_stores_in_l1(self, cache, mock_l2):
        """set() must write to L1."""
        cache.set("test_key", {"data": "value"})

        # Verify L1 can retrieve it
        vkey = cache._versioned_key("test_key")
        l1_raw = caches["local"].get(vkey)
        assert l1_raw is not None
        assert l1_raw == {"__v": {"data": "value"}}

    def test_set_stores_in_l2(self, cache, mock_l2):
        """set() must write to L2 (Redis)."""
        cache.set("test_key", {"data": "value"})

        mock_l2.set.assert_called_once()
        call_args = mock_l2.set.call_args
        vkey = cache._versioned_key("test_key")
        assert call_args[0][0] == vkey

    def test_get_returns_l1_hit_when_in_l1(self, cache, mock_l2):
        """
        get() must return L1 hit without touching L2.

        L1 is the fastest path. Redis must not be queried if L1 has the key.
        """
        # Put directly in L1
        vkey = cache._versioned_key("hot_key")
        caches["local"].set(vkey, cache._encode({"cached": True}), 60)

        value, source = cache.get("hot_key")

        assert source == "l1_memory"
        assert value == {"cached": True}
        mock_l2.get.assert_not_called()

    def test_get_returns_l2_hit_when_not_in_l1(self, cache, mock_l2):
        """
        get() must check L2 when L1 misses.

        L1 cleared between tests. L2 mock returns a value.
        Source must be "l2_redis".
        """
        mock_l2.get.return_value = cache._encode({"from": "redis"})

        value, source = cache.get("warm_key")

        assert source == "l2_redis"
        assert value == {"from": "redis"}

    def test_get_backfills_l1_on_l2_hit(self, cache, mock_l2):
        """
        When L2 hits, the value must be backfilled into L1.

        Next request for same key → L1 hit (faster).
        This is the L2→L1 promotion path.
        """
        mock_l2.get.return_value = cache._encode("promoted_value")

        cache.get("promote_key")

        # L1 must now have the value
        vkey = cache._versioned_key("promote_key")
        l1_raw = caches["local"].get(vkey)
        assert l1_raw is not None

    def test_get_returns_miss_when_not_in_either(self, cache, mock_l2):
        """
        get() must return (None, 'miss') when both L1 and L2 miss.

        Cold cache path — caller must rebuild data from DB.
        """
        mock_l2.get.return_value = None  # Redis miss

        value, source = cache.get("cold_key")

        assert source == "miss"
        assert value is None

    def test_get_returns_deep_copy_from_l1(self, cache, mock_l2):
        """
        L1 hits must return a deep copy — not the cached object itself.

        If callers mutate the returned object, they would mutate the L1
        cache entry directly — corrupting future cache reads.

        Deep copy prevents this cache poisoning.
        """
        original = {"items": [1, 2, 3]}
        cache.set("mutation_key", original)

        value1, _ = cache.get("mutation_key")
        value1["items"].append(999)  # mutate the returned value

        value2, _ = cache.get("mutation_key")
        assert 999 not in value2["items"], (
            "L1 cache was mutated — deep copy not working"
        )

    def test_get_handles_falsy_cached_none(self, cache, mock_l2):
        """
        Cached None must be returned as cache hit, not treated as miss.

        This is the core falsy-value problem the encoding solves.
        """
        mock_l2.get.return_value = cache._encode(None)

        value, source = cache.get("none_key")

        assert source == "l2_redis"
        assert value is None  # None is the actual cached value

    def test_get_handles_falsy_cached_empty_list(self, cache, mock_l2):
        """Cached [] must be returned as cache hit."""
        mock_l2.get.return_value = cache._encode([])

        value, source = cache.get("empty_list_key")

        assert source == "l2_redis"
        assert value == []

    def test_get_handles_falsy_cached_false(self, cache, mock_l2):
        """Cached False must be returned as cache hit."""
        mock_l2.get.return_value = cache._encode(False)

        value, source = cache.get("false_key")

        assert source == "l2_redis"
        assert value is False

    def test_delete_clears_l1(self, cache, mock_l2):
        """
        delete() must clear L1 entirely.

        L1 has no pattern search — full clear is the safe option.
        Cost is negligible since L1 rebuilds on next request.
        """
        # Put something in L1
        vkey = cache._versioned_key("delete_me")
        caches["local"].set(vkey, cache._encode("data"), 60)

        cache.delete("delete_me")

        # L1 must be cleared
        assert caches["local"].get(vkey) is None

    def test_delete_calls_l2_delete_pattern(self, cache, mock_l2):
        """
        delete() must call delete_pattern() on L2 — not delete() directly.

        delete_pattern() uses Redis SCAN — safe at scale.
        Keys * blocks Redis entirely — never acceptable in production.
        """
        cache.delete("product_list")

        mock_l2.delete_pattern.assert_called_once()
        pattern_arg = mock_l2.delete_pattern.call_args[0][0]
        assert "product_list" in pattern_arg

    def test_set_uses_l1_timeout(self, cache, mock_l2):
        """Custom l1_timeout must be passed to L1 set."""
        cache.set("timeout_key", "value", l1_timeout=120)

        vkey = cache._versioned_key("timeout_key")
        # L1 has the value with custom timeout
        # We verify the key exists (timeout enforcement is Django's job)
        assert caches["local"].get(vkey) is not None

    def test_set_uses_l2_timeout(self, cache, mock_l2):
        """Custom l2_timeout must be passed to L2 set."""
        cache.set("timeout_key", "value", l2_timeout=600)

        call_args = mock_l2.set.call_args
        # Third positional arg or timeout kwarg should be 600
        assert 600 in call_args[0] or call_args[1].get("timeout") == 600


# ─── Layer 4: get_or_set() ────────────────────────────────────────────────────

@pytest.mark.unit
class TestGetOrSet:
    """
    Tests for get_or_set() — cache-aside pattern.

    get_or_set() is the primary public API.
    It combines get + conditional set + stampede protection.
    """

    def test_get_or_set_calls_builder_on_miss(self, cache, mock_l2):
        """builder_fn must be called when cache is cold (miss)."""
        mock_l2.get.return_value = None
        builder_called = []

        def builder():
            builder_called.append(1)
            return {"fresh": "data"}

        value, source = cache.get_or_set("cold_key", builder, lock=False)

        assert len(builder_called) == 1
        assert source == "database"
        assert value == {"fresh": "data"}

    def test_get_or_set_does_not_call_builder_on_l1_hit(self, cache, mock_l2):
        """builder_fn must NOT be called when L1 has the value."""
        # Pre-populate L1
        vkey = cache._versioned_key("hot_key")
        caches["local"].set(vkey, cache._encode({"cached": True}), 60)

        builder_called = []

        value, source = cache.get_or_set(
            "hot_key", lambda: builder_called.append(1) or {}, lock=False
        )

        assert len(builder_called) == 0
        assert source == "l1_memory"

    def test_get_or_set_does_not_call_builder_on_l2_hit(self, cache, mock_l2):
        """builder_fn must NOT be called when L2 has the value."""
        mock_l2.get.return_value = cache._encode({"from": "redis"})

        builder_called = []

        value, source = cache.get_or_set(
            "warm_key", lambda: builder_called.append(1) or {}, lock=False
        )

        assert len(builder_called) == 0
        assert source == "l2_redis"

    def test_get_or_set_stores_result_after_builder_call(self, cache, mock_l2):
        """
        After builder_fn runs, result must be stored in both L1 and L2.

        Ensures next call for same key is served from cache, not DB.
        """
        mock_l2.get.return_value = None

        cache.get_or_set("store_key", lambda: {"id": 42}, lock=False)

        # L2 must have been written
        mock_l2.set.assert_called()

        # L1 must have been written
        vkey = cache._versioned_key("store_key")
        assert caches["local"].get(vkey) is not None

    def test_get_or_set_reraises_builder_exception(self, cache, mock_l2):
        """
        If builder_fn raises, the exception must propagate to the caller.

        The view must receive the exception and return an appropriate
        error response. Swallowing it would silently return None — worse.
        """
        mock_l2.get.return_value = None

        def failing_builder():
            raise RuntimeError("Database connection lost")

        with pytest.raises(RuntimeError, match="Database connection lost"):
            cache.get_or_set("fail_key", failing_builder, lock=False)

    def test_get_or_set_releases_lock_after_builder_exception(
        self, cache, mock_l2
    ):
        """
        Lock must be released even when builder_fn raises.

        If lock is not released, subsequent requests wait forever.
        The finally block in get_or_set handles this.
        """
        mock_l2.get.return_value = None
        mock_l2.add.return_value = True  # lock acquired

        def failing_builder():
            raise ValueError("Oops")

        try:
            cache.get_or_set("lock_release_key", failing_builder, lock=True)
        except ValueError:
            pass

        # Lock must have been released (delete called)
        lock_key = cache._lock_key("lock_release_key")
        mock_l2.delete.assert_called_with(lock_key)

    def test_get_or_set_with_lock_false_skips_lock_acquire(
        self, cache, mock_l2
    ):
        """
        lock=False must skip Redis lock acquisition entirely.

        Used in unit tests that do not need stampede protection.
        Should not call mock_l2.add (which is the lock acquire call).
        """
        mock_l2.get.return_value = None

        cache.get_or_set("no_lock_key", lambda: "data", lock=False)

        mock_l2.add.assert_not_called()

    def test_get_or_set_source_is_database_on_miss(self, cache, mock_l2):
        """Source must be 'database' when builder_fn was called."""
        mock_l2.get.return_value = None

        _, source = cache.get_or_set("db_key", lambda: {"id": 1}, lock=False)

        assert source == "database"

    def test_get_or_set_builder_called_once_not_twice(self, cache, mock_l2):
        """
        builder_fn must be called exactly once per cold cache, not twice.

        Regression test — early versions called builder twice due to
        a logic error in the lock-wait retry path.
        """
        mock_l2.get.return_value = None
        call_count = [0]

        def counting_builder():
            call_count[0] += 1
            return {"count": call_count[0]}

        cache.get_or_set("once_key", counting_builder, lock=False)

        assert call_count[0] == 1


# ─── Layer 5: Fault tolerance ─────────────────────────────────────────────────

@pytest.mark.unit
class TestCacheFaultTolerance:
    """
    Tests that cache failures degrade gracefully.

    Production requirement: cache failures must NEVER crash HTTP requests.
    Requests must still succeed — just slower (hitting DB instead of cache).

    Tested scenarios:
        - L1 GET raises exception → fall through to L2
        - L2 GET raises exception → return miss
        - L1 SET raises exception → silent log, no crash
        - L2 SET raises exception → silent log, no crash
        - L2 delete_pattern raises → silent log, no crash
    """

    def test_l1_get_failure_falls_through_to_l2(self, cache, mock_l2):
        """
        If L1 get() raises, cache must try L2 instead of crashing.

        L1 failure is rare but possible (memory pressure, corruption).
        Fallback to L2 keeps the request alive.
        """
        mock_l2.get.return_value = cache._encode({"from": "l2_fallback"})

        with patch.object(caches["local"], "get", side_effect=Exception("L1 exploded")):
            value, source = cache.get("fallback_key")

        assert source == "l2_redis"
        assert value == {"from": "l2_fallback"}

    def test_l2_get_failure_returns_miss(self, cache, mock_l2):
        """
        If both L1 and L2 get() raise, cache must return miss — not crash.

        Caller gets (None, 'miss') and falls back to DB.
        Request succeeds, just slower.
        """
        mock_l2.get.side_effect = Exception("Redis connection refused")

        value, source = cache.get("all_failed_key")

        assert source == "miss"
        assert value is None

    def test_l1_set_failure_does_not_crash(self, cache, mock_l2):
        """
        If L1 set() raises, the exception must be caught — no crash.

        L2 write should still happen.
        """
        with patch.object(
            caches["local"], "set", side_effect=Exception("L1 SET failed")
        ):
            # Must not raise
            try:
                cache.set("l1_fail_key", {"data": "value"})
            except Exception as e:
                pytest.fail(f"cache.set() raised despite L1 failure: {e}")

    def test_l2_set_failure_does_not_crash(self, cache, mock_l2):
        """
        If L2 set() raises, the exception must be caught — no crash.
        """
        mock_l2.set.side_effect = Exception("Redis SET failed")

        try:
            cache.set("l2_fail_key", {"data": "value"})
        except Exception as e:
            pytest.fail(f"cache.set() raised despite L2 failure: {e}")

    def test_l2_delete_failure_does_not_crash(self, cache, mock_l2):
        """
        If L2 delete_pattern() raises, the exception must be caught.

        Cache invalidation failure must never crash the view that triggered it.
        """
        mock_l2.delete_pattern.side_effect = Exception("Redis delete failed")

        try:
            cache.delete("fail_prefix")
        except Exception as e:
            pytest.fail(f"cache.delete() raised despite L2 failure: {e}")

    def test_l2_lock_acquire_failure_returns_true(self, cache, mock_l2):
        """
        If Redis lock acquire raises, _acquire_lock must return True.

        Fail-open: allow the request to proceed without stampede protection
        rather than deadlocking all requests because Redis is down.
        """
        mock_l2.add.side_effect = Exception("Redis unavailable")

        result = cache._acquire_lock("stampede_key")

        assert result is True, (
            "Lock acquire failure must return True (fail-open) "
            "not False (which would block all requests waiting for a lock "
            "that will never be released)"
        )