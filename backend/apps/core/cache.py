"""
Two-level cache: L1 (memory) → L2 (Redis) → Database
"""
import logging
from django.core.cache import caches

logger = logging.getLogger('apps.core')


class TwoLevelCache:
    """
    Transparent two-level cache.
    L1 = in-memory (fast, per-process, short TTL)
    L2 = Redis (shared, persistent, longer TTL)
    """

    def __init__(self, l1_timeout=60, l2_timeout=300):
        self.l1 = caches['local']
        self.l2 = caches['default']
        self.l1_timeout = l1_timeout
        self.l2_timeout = l2_timeout

    def get(self, key):
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            logger.debug("Cache HIT L1 (memory): %s", key)
            return value, 'l1_memory'

        # Try L2
        value = self.l2.get(key)
        if value is not None:
            logger.debug("Cache HIT L2 (redis): %s", key)
            # Populate L1 for next request
            self.l1.set(key, value, self.l1_timeout)
            return value, 'l2_redis'

        logger.debug("Cache MISS both levels: %s", key)
        return None, 'miss'

    def set(self, key, value):
        # Write to both levels
        self.l1.set(key, value, self.l1_timeout)
        self.l2.set(key, value, self.l2_timeout)
        logger.debug("Cache SET both levels: %s", key)

    def delete(self, prefix: str):
        """Delete all keys starting with prefix from both L1 and L2."""
        # L2 Redis — supports pattern deletion
        from django_redis import get_redis_connection
        redis_client = get_redis_connection("default")
        pattern = f"*{prefix}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.debug("Cache DELETE pattern L2: %s (%d keys)", pattern, len(keys))

        # L1 memory — no pattern support, clear entirely
        self.l1.clear()
        logger.debug("Cache CLEAR L1 (memory) on pattern delete: %s", prefix)
       



# Single instance to use across the project
two_level_cache = TwoLevelCache(l1_timeout=60, l2_timeout=300)