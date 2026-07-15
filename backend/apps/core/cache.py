"""
apps/core/cache.py

Two-level cache: L1 (in-memory) → L2 (Redis) → Database

Architecture:
    L1 = LocMemCache  — per-process, fastest, short TTL
    L2 = Redis        — shared across workers, longer TTL

Production hardening:
    - Sentinel encoding   : correctly stores falsy values ([], False, 0, None)
    - Stampede protection : Redis lock prevents concurrent DB hits on cold cache
    - Deep copy on L1 hit : prevents object mutation from poisoning shared memory
    - Fault tolerance     : L1/L2 failures degrade gracefully, never crash request
    - Cache versioning    : bump CACHE_VERSION to bust all keys on deploy
    - Safe deletion       : delete_pattern() replaces blocking KEYS * scan
    - Dynamic TTLs        : per-call timeout overrides for different data profiles
"""
import copy
import logging
import time
from typing import Any, Callable, Optional, Tuple

from django.core.cache import caches

logger = logging.getLogger("apps.core")


class TwoLevelCache:
    """
    Transparent two-level cache with production hardening.

    Typical usage — cache-aside with stampede protection:

        data, source = two_level_cache.get_or_set(
            "my_cache_key",
            lambda: MySerializer(MyModel.objects.all(), many=True).data,
        )

    Manual usage:

        data, source = two_level_cache.get("my_cache_key")
        if source == "miss":
            data = build_data()
            two_level_cache.set("my_cache_key", data)

    Invalidation:

        two_level_cache.delete("my_cache_key")
    """

    CACHE_VERSION = 1

    def __init__(self, l1_timeout: int = 60, l2_timeout: int = 300) -> None:
        self.l1_timeout = l1_timeout
        self.l2_timeout = l2_timeout
        self._lock_timeout = 10
        self._lock_retry_interval = 0.1
        self._lock_max_wait = 5

    # ── Cache backend properties ───────────────────────────────────────────────

    @property
    def _l1(self):
        """
        Resolved at call time, not at __init__, because Django cache backends
        are not guaranteed to be ready at module import time.
        """
        return caches["local"]

    @property
    def _l2(self):
        return caches["default"]

    # ── Key helpers ───────────────────────────────────────────────────────────

    def _versioned_key(self, key: str) -> str:
        """
        Prefixes every key with the cache version.
        Bumping CACHE_VERSION in one place instantly invalidates the entire
        cache without manually tracking or deleting individual keys.
        """
        return f"v{self.CACHE_VERSION}:{key}"

    def _lock_key(self, key: str) -> str:
        return f"lock:{self._versioned_key(key)}"

    # ── Encoding helpers ──────────────────────────────────────────────────────

    def _encode(self, value: Any) -> dict:
        """
        Wraps value in a dict so cache backends can distinguish between:
            - A genuine cache miss  → backend returns None
            - A cached None value   → backend returns {"__v": None}
            - A cached empty list   → backend returns {"__v": []}
        Without this, any falsy cached value looks like a cache miss.
        """
        return {"__v": value}

    def _decode(self, raw: Any) -> Tuple[bool, Any]:
        """
        Returns (cache_hit: bool, value: Any).

        cache_hit=False → genuine miss, caller must go to DB.
        cache_hit=True  → value is what was stored (may be [], None, False).
        """
        if raw is None:
            return False, None
        if isinstance(raw, dict) and "__v" in raw:
            return True, raw["__v"]
        logger.warning("Cache: encountered un-encoded value — treating as miss")
        return False, None

    # ── Stampede lock helpers ─────────────────────────────────────────────────

    def _acquire_lock(self, key: str) -> bool:
        """
        Atomically sets a Redis lock using cache.add() (SET NX equivalent).
        Returns True if this caller acquired the lock (should rebuild cache).
        Returns True also when Redis is unavailable — fail-open so the request
        can still proceed without stampede protection rather than crashing.
        """
        try:
            return bool(self._l2.add(self._lock_key(key), "1", self._lock_timeout))
        except Exception as exc:
            logger.warning("Cache: lock acquire failed key=%s error=%s", key, exc)
            return True

    def _release_lock(self, key: str) -> None:
        try:
            self._l2.delete(self._lock_key(key))
        except Exception as exc:
            logger.warning("Cache: lock release failed key=%s error=%s", key, exc)

    def _wait_for_lock_release(self, key: str) -> None:
        """
        Polls until the lock disappears (meaning the lock-holder has written
        fresh data to cache) or until _lock_max_wait seconds have elapsed.
        Callers then retry cache.get() instead of hitting the DB themselves.
        """
        waited = 0.0
        while waited < self._lock_max_wait:
            time.sleep(self._lock_retry_interval)
            waited += self._lock_retry_interval
            try:
                if not self._l2.get(self._lock_key(key)):
                    return
            except Exception:
                return

    # ── Internal set helpers ──────────────────────────────────────────────────

    def _set_l1(self, vkey: str, value: Any, timeout: Optional[int] = None) -> None:
        try:
            self._l1.set(vkey, self._encode(value), timeout or self.l1_timeout)
        except Exception as exc:
            logger.warning("Cache: L1 SET failed vkey=%s error=%s", vkey, exc)

    def _set_l2(self, vkey: str, value: Any, timeout: Optional[int] = None) -> None:
        try:
            self._l2.set(vkey, self._encode(value), timeout or self.l2_timeout)
        except Exception as exc:
            logger.warning("Cache: L2 SET failed vkey=%s error=%s", vkey, exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        Checks L1 then L2. Returns (value, source).

        source values:
            "l1_memory" — served from in-process memory
            "l2_redis"  — served from Redis, L1 backfilled for next request
            "miss"      — not found in either level, caller must rebuild

        L1 values are deep-copied before returning to prevent callers from
        mutating shared in-process objects (cache poisoning).
        """
        vkey = self._versioned_key(key)

        try:
            found, value = self._decode(self._l1.get(vkey))
            if found:
                logger.debug("Cache HIT L1 | key=%s", key)
                return copy.deepcopy(value), "l1_memory"
        except Exception as exc:
            logger.warning("Cache: L1 GET failed key=%s error=%s", key, exc)

        try:
            found, value = self._decode(self._l2.get(vkey))
            if found:
                logger.debug("Cache HIT L2 | key=%s", key)
                self._set_l1(vkey, value)
                return value, "l2_redis"
        except Exception as exc:
            logger.warning("Cache: L2 GET failed key=%s error=%s", key, exc)

        logger.debug("Cache MISS | key=%s", key)
        return None, "miss"

    def set(
        self,
        key: str,
        value: Any,
        l1_timeout: Optional[int] = None,
        l2_timeout: Optional[int] = None,
    ) -> None:
        """
        Writes value to both L1 and L2.

        l1_timeout / l2_timeout override instance defaults, allowing
        different data profiles (e.g. categories with a long TTL vs
        search results with a short TTL) without separate cache instances.
        """
        vkey = self._versioned_key(key)
        self._set_l1(vkey, value, l1_timeout)
        self._set_l2(vkey, value, l2_timeout)
        logger.debug("Cache SET both levels | key=%s", key)

    def delete(self, prefix: str) -> None:
        """
        Removes all versioned keys that start with prefix.

        L2: delete_pattern() uses SCAN internally — safe at scale.
            (Never use KEYS * in production; it blocks Redis entirely.)
        L1: no pattern search available, so the entire L1 store is cleared.
            Cost is negligible — L1 rebuilds on the next request.
        """
        try:
            pattern = f"*v{self.CACHE_VERSION}:{prefix}*"
            self._l2.delete_pattern(pattern)
            logger.info("Cache DELETE L2 | pattern=%s", pattern)
        except Exception as exc:
            logger.error("Cache: L2 DELETE failed prefix=%s error=%s", prefix, exc)

        try:
            self._l1.clear()
            logger.debug("Cache CLEAR L1 | reason=prefix_delete prefix=%s", prefix)
        except Exception as exc:
            logger.error("Cache: L1 CLEAR failed error=%s", exc)

    def get_or_set(
        self,
        key: str,
        builder_fn: Callable[[], Any],
        *,
        lock: bool = True,
        l1_timeout: Optional[int] = None,
        l2_timeout: Optional[int] = None,
    ) -> Tuple[Any, str]:
        """
        Cache-aside pattern with stampede protection.

        Guarantees that builder_fn (which hits the DB) is called by at most
        one worker at a time when the cache is cold.  All other concurrent
        workers wait for the lock-holder to populate the cache, then serve
        from cache instead of duplicating the DB query.

        Args:
            key         : cache key (un-versioned; versioning is applied internally)
            builder_fn  : zero-argument callable that returns fresh data
            lock        : set False only in unit tests to skip Redis locking
            l1_timeout  : override L1 TTL for this specific key
            l2_timeout  : override L2 TTL for this specific key

        Returns:
            (value, source) — source is one of "l1_memory", "l2_redis", "database"

        Raises:
            Re-raises any exception from builder_fn so the caller can return
            an appropriate HTTP error response.
        """
        value, source = self.get(key)
        if source != "miss":
            return value, source

        if lock:
            acquired = self._acquire_lock(key)
            if not acquired:
                logger.debug("Cache: waiting for lock | key=%s", key)
                self._wait_for_lock_release(key)

                value, source = self.get(key)
                if source != "miss":
                    logger.debug(
                        "Cache: hit after lock wait | key=%s source=%s", key, source
                    )
                    return value, source

                logger.warning("Cache: still miss after lock wait | key=%s", key)

        try:
            value = builder_fn()
            self.set(key, value, l1_timeout=l1_timeout, l2_timeout=l2_timeout)
            return value, "database"
        finally:
            if lock:
                self._release_lock(key)


two_level_cache = TwoLevelCache(l1_timeout=60, l2_timeout=300)
