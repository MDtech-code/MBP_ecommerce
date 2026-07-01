"""
Two-level cache: L1 (memory) → L2 (Redis) → Database

Fixes applied:
- Falsy value cache miss: use sentinel pattern
- Cache stampede: distributed lock via Redis
- Error handling: backend failures are caught and logged
- Cache versioning: invalidate on deploy
"""
import time
import logging
import copy
from typing import Any, Tuple, Optional
from django.core.cache import caches

logger = logging.getLogger("apps.core")

# ─── Sentinel ─────────────────────────────────────────────────────────────────
# Why: cached [] or False or 0 would look like a cache miss without this.
# We store this object IN the cache to mean "we cached an empty/falsy value".
_SENTINEL = "__CACHED_EMPTY__"


class TwoLevelCache:
    """
    Transparent two-level cache with production hardening.

    L1 = in-memory (fast, per-process, short TTL)
    L2 = Redis (shared, persistent, longer TTL)

    Features:
        - Sentinel pattern: correctly caches falsy values ([], False, 0, {})
        - Stampede protection: only one worker rebuilds cache under lock
        - Fault tolerance: L1/L2 failures degrade gracefully, never crash
        - Cache versioning: bump CACHE_VERSION in settings to bust on deploy
    """

    # Why class-level: shared across all instances, easy to bump on deploy
    CACHE_VERSION = 1

    def __init__(self, l1_timeout: int = 60, l2_timeout: int = 300):
        self.l1_timeout = l1_timeout
        self.l2_timeout = l2_timeout

        # Lock config for stampede protection
        # Why 10s: long enough for a slow DB query, short enough to not block forever
        self._lock_timeout = 10
        self._lock_retry_interval = 0.1  # 100ms between retries
        self._lock_max_wait = 5          # max 5s waiting for another worker

    # ─── Internal helpers ──────────────────────────────────────────────────

    @property
    def _l1(self):
        """
        Why property: avoids storing cache backend at __init__ time.
        Django cache backends may not be ready at module import.
        """
        return caches["local"]

    @property
    def _l2(self):
        return caches["default"]

    def _versioned_key(self, key: str) -> str:
        """
        Why: bumping CACHE_VERSION instantly invalidates all cached data
        without needing to track and delete individual keys.
        Useful after schema changes or deploys.
        """
        return f"v{self.CACHE_VERSION}:{key}"

    def _encode(self, value: Any) -> Any:
        """
        Why: we need to distinguish between:
        - Cache miss  → None returned by backend
        - Cached None → we explicitly stored None
        - Cached []   → we explicitly stored empty list

        Solution: wrap value so None/[]/False all become storable.
        """
        return {"__v": value}

    def _decode(self, raw: Any) -> Tuple[bool, Any]:
        """
        Returns (found, value).
        found=False means actual cache miss.
        found=True, value=[] means we cached an empty list — valid hit.
        """
        if raw is None:
            return False, None
        if isinstance(raw, dict) and "__v" in raw:
            return True, raw["__v"]
        # Legacy data without encoding — treat as miss to re-cache cleanly
        logger.warning("Cache: found un-encoded value, treating as miss")
        return False, None

    # ─── Lock helpers (stampede protection) ───────────────────────────────

    def _lock_key(self, key: str) -> str:
        return f"lock:{self._versioned_key(key)}"

    def _acquire_lock(self, key: str) -> bool:
        """
        Why: Redis SET NX (set if not exists) is atomic.
        Only one worker can set the lock; others see it exists and wait.
        This prevents 100 concurrent requests all hitting the DB simultaneously
        on a cold cache (stampede).
        """
        lock_key = self._lock_key(key)
        try:
            result = self._l2.add(lock_key, "1", self._lock_timeout)
            return bool(result)
        except Exception as exc:
            # Why: if Redis is down, we cannot lock — degrade gracefully
            # by allowing the request through (no stampede protection, but no crash)
            logger.warning(
                "Cache: failed to acquire lock for key=%s error=%s", key, exc
            )
            return True  # Fail open: let the request proceed

    def _release_lock(self, key: str) -> None:
        try:
            self._l2.delete(self._lock_key(key))
        except Exception as exc:
            logger.warning(
                "Cache: failed to release lock for key=%s error=%s", key, exc
            )

    def _wait_for_lock_release(self, key: str) -> None:
        """
        Why: instead of hammering DB, waiting workers poll until the
        lock-holder writes to cache, then they serve from cache.
        """
        lock_key = self._lock_key(key)
        waited = 0.0
        while waited < self._lock_max_wait:
            time.sleep(self._lock_retry_interval)
            waited += self._lock_retry_interval
            try:
                if not self._l2.get(lock_key):
                    return  # Lock released — cache should be warm now
            except Exception:
                return  # Redis error — stop waiting, proceed

    # ─── Public API ───────────────────────────────────────────────────────

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        Returns (value, source) where source is 'l1_memory' | 'l2_redis' | 'miss'.

        Why return source: lets callers log/metric where data came from
        without coupling cache logic to observability.
        """
        vkey = self._versioned_key(key)

        # ── L1 (in-memory) ────────────────────────────────────────────────
        try:
            raw = self._l1.get(vkey)
            found, value = self._decode(raw)
            if found:
                logger.debug("Cache HIT L1 | key=%s", key)
                # return value, "l1_memory"
                return copy.deepcopy(value), "l1_memory"
        except Exception as exc:
            # Why: L1 failure must not crash the request — degrade to L2
            logger.warning("Cache: L1 GET failed key=%s error=%s", key, exc)

        # ── L2 (Redis) ────────────────────────────────────────────────────
        try:
            raw = self._l2.get(vkey)
            found, value = self._decode(raw)
            if found:
                logger.debug("Cache HIT L2 | key=%s", key)
                # Backfill L1 so next request is faster
                self._set_l1(vkey, value)
                return value, "l2_redis"
        except Exception as exc:
            # Why: Redis down must not crash the request — degrade to DB
            logger.warning("Cache: L2 GET failed key=%s error=%s", key, exc)

        logger.debug("Cache MISS | key=%s", key)
        return None, "miss"

    def set(self, key: str, value: Any, l1_timeout: Optional[int] = None, l2_timeout: Optional[int] = None) -> None:
        """
        Write to both L1 and L2.with optional dynamic timeouts.

        Why encode: ensures [] and False are stored and retrieved correctly.
        """
        vkey = self._versioned_key(key)
        self._set_l1(vkey, value, l1_timeout)
        self._set_l2(vkey, value, l2_timeout)
        logger.debug("Cache SET both levels | key=%s", key)

    def _set_l1(self, vkey: str, value: Any, timeout: Optional[int] = None) -> None:
        try:
            # Use provided timeout, otherwise fall back to self.l1_timeout
            t = timeout if timeout is not None else self.l1_timeout
            self._l1.set(vkey, self._encode(value), t)
        except Exception as exc:
            logger.warning("Cache: L1 SET failed vkey=%s error=%s", vkey, exc)

    def _set_l2(self, vkey: str, value: Any, timeout: Optional[int] = None) -> None:
        try:
            # Use provided timeout, otherwise fall back to self.l2_timeout
            t = timeout if timeout is not None else self.l2_timeout
            self._l2.set(vkey, self._encode(value), t)
        except Exception as exc:
            logger.warning("Cache: L2 SET failed vkey=%s error=%s", vkey, exc)

    def delete(self, prefix: str) -> None:
        """
        Delete all keys matching prefix from both cache levels.

        Why clear all L1: in-memory cache has no pattern search.
        Small cost (L1 rebuilds quickly) vs correctness guarantee.
        """
        # ── L2 Redis pattern delete ────────────────────────────────────────
        try:
            # from django_redis import get_redis_connection
            # redis_client = get_redis_connection("default")
            # Why versioned pattern: only delete keys for current version
            pattern = f"*v{self.CACHE_VERSION}:{prefix}*"
            # keys = redis_client.keys(pattern)
            self._l2.delete_pattern(pattern)
            logger.info("Cache DELETE L2 | pattern=%s safely deleted", pattern)
            # if keys:
            #     redis_client.delete(*keys)
            #     logger.info(
            #         "Cache DELETE L2 | pattern=%s keys_deleted=%d",
            #         pattern,
            #         len(keys),
            #     )
        except Exception as exc:
            logger.error("Cache: L2 DELETE failed prefix=%s error=%s", prefix, exc)

        # ── L1 clear (no pattern support) ─────────────────────────────────
        try:
            self._l1.clear()
            logger.debug("Cache CLEAR L1 | triggered by prefix=%s", prefix)
        except Exception as exc:
            logger.error("Cache: L1 CLEAR failed error=%s", exc)

    def get_or_set(
        self,
        key: str,
        builder_fn,
        *,
        lock: bool = True,
        l1_timeout: Optional[int] = None,
        l2_timeout: Optional[int] = None,
    ) -> Tuple[Any, str]:
        """
        Cache-aside pattern with optional stampede protection.

        Why this method: callers shouldn't implement get→miss→DB→set
        themselves — that pattern is where stampede bugs appear.

        Usage:
            data, source = two_level_cache.get_or_set(
                "my_key",
                lambda: MySerializer(MyModel.objects.all(), many=True).data
            )

        Args:
            key: cache key
            builder_fn: callable that returns fresh data (hits DB)
            lock: enable stampede protection (disable only in tests)
        """
        # 1. Try cache first (fast path — no lock needed)
        value, source = self.get(key)
        if source != "miss":
            return value, source

        # 2. Cache miss — try to acquire lock
        if lock:
            acquired = self._acquire_lock(key)
            if not acquired:
                # Another worker is rebuilding — wait, then try cache again
                logger.debug("Cache: waiting for lock release | key=%s", key)
                self._wait_for_lock_release(key)

                # Try cache again after waiting
                value, source = self.get(key)
                if source != "miss":
                    logger.debug(
                        "Cache: served from cache after lock wait | key=%s source=%s",
                        key, source,
                    )
                    return value, source

                # Still a miss (lock holder failed?) — fall through to DB
                logger.warning(
                    "Cache: still miss after lock wait | key=%s", key
                )

        # 3. We hold the lock (or lock=False) — hit DB and populate cache
        try:
            value = builder_fn()
            self.set(key, value, l1_timeout=l1_timeout, l2_timeout=l2_timeout)
            return value, "database"
        finally:
            if lock:
                self._release_lock(key)


# ─── Singleton ────────────────────────────────────────────────────────────────
two_level_cache = TwoLevelCache(l1_timeout=60, l2_timeout=300)