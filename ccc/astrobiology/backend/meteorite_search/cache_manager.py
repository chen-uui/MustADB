import hashlib
import json
import logging
from typing import Any, Dict, List, Set

from django.core.cache import cache


logger = logging.getLogger(__name__)


class MeteoriteCacheManager:
    """Meteorite search cache manager."""

    CACHE_PREFIX = "meteorite"
    CACHE_TIMEOUT = 3600
    KEY_REGISTRY_SUFFIX = "keys"

    @staticmethod
    def _generate_cache_key(params: Dict[str, Any]) -> str:
        """Generate a deterministic cache key from request params."""
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        hashed = hashlib.md5(params_str.encode()).hexdigest()
        return f"{MeteoriteCacheManager.CACHE_PREFIX}:{hashed}"

    @staticmethod
    def _registry_key() -> str:
        return f"{MeteoriteCacheManager.CACHE_PREFIX}:{MeteoriteCacheManager.KEY_REGISTRY_SUFFIX}"

    @staticmethod
    def _get_registered_keys() -> Set[str]:
        stored = cache.get(MeteoriteCacheManager._registry_key())
        if not stored:
            return set()

        if isinstance(stored, str):
            try:
                stored = json.loads(stored)
            except Exception:
                return set()

        if isinstance(stored, (list, tuple, set)):
            return {str(item) for item in stored if item}

        return set()

    @staticmethod
    def _register_cache_key(cache_key: str) -> None:
        keys = MeteoriteCacheManager._get_registered_keys()
        if cache_key in keys:
            return

        keys.add(cache_key)
        cache.set(
            MeteoriteCacheManager._registry_key(),
            json.dumps(sorted(keys)),
            MeteoriteCacheManager.CACHE_TIMEOUT * 24,
        )

    @staticmethod
    def get_search_results(params: Dict[str, Any]) -> List[Dict]:
        """Return cached search results if present."""
        cache_key = MeteoriteCacheManager._generate_cache_key(params)
        cached_data = cache.get(cache_key)

        if cached_data:
            return json.loads(cached_data)
        return None

    @staticmethod
    def set_search_results(params: Dict[str, Any], results: List[Dict]):
        """Store search results in the configured Django cache backend."""
        cache_key = MeteoriteCacheManager._generate_cache_key(params)
        cache.set(cache_key, json.dumps(results), MeteoriteCacheManager.CACHE_TIMEOUT)
        MeteoriteCacheManager._register_cache_key(cache_key)

    @staticmethod
    def invalidate_search_cache():
        """Invalidate meteorite-related cache entries safely across backends."""
        pattern = f"{MeteoriteCacheManager.CACHE_PREFIX}:*"

        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
            cache.delete(MeteoriteCacheManager._registry_key())
            return

        deleted = 0
        for cache_key in MeteoriteCacheManager._get_registered_keys():
            cache.delete(cache_key)
            deleted += 1
        cache.delete(MeteoriteCacheManager._registry_key())
        logger.info(
            "invalidate_search_cache fallback backend=%s deleted=%s",
            type(getattr(cache, "_cache", cache)).__name__,
            deleted,
        )

    @staticmethod
    def get_options_cache():
        """Return cached search options if present."""
        return cache.get(f"{MeteoriteCacheManager.CACHE_PREFIX}:options")

    @staticmethod
    def set_options_cache(data: Dict):
        """Store search options in the configured Django cache backend."""
        cache_key = f"{MeteoriteCacheManager.CACHE_PREFIX}:options"
        cache.set(
            cache_key,
            json.dumps(data),
            MeteoriteCacheManager.CACHE_TIMEOUT * 24,
        )
        MeteoriteCacheManager._register_cache_key(cache_key)
