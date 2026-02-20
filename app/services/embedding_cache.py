import hashlib
import time
import threading
import os
import sys
from typing import Dict, List, Optional, Tuple
from collections import OrderedDict


class EmbeddingCache:
    """
    Enterprise-grade in-memory embedding cache.

    Features:
    - LRU eviction
    - TTL expiration
    - Thread-safe (RLock)
    - Tenant isolation
    - Configurable via ENV
    - Hit/miss statistics
    - Memory usage estimation
    - Optional memory cap
    - Safe for single-instance production
    """

    # ==========================================================
    # Configuration (ENV Controlled)
    # ==========================================================

    MAX_SIZE = int(os.getenv("EMBED_CACHE_MAX_SIZE", 5000))
    TTL_SECONDS = int(os.getenv("EMBED_CACHE_TTL_SECONDS", 60 * 60 * 6))  # 6h
    ENABLED = os.getenv("EMBED_CACHE_ENABLED", "true").lower() == "true"

    # Optional hard memory cap (MB) — 0 disables
    MAX_MEMORY_MB = float(os.getenv("EMBED_CACHE_MAX_MEMORY_MB", "0"))

    # ==========================================================
    # Internal Storage
    # key → (embedding, timestamp)
    # ==========================================================

    _cache: "OrderedDict[str, Tuple[List[float], float]]" = OrderedDict()
    _lock = threading.RLock()

    _hits = 0
    _misses = 0

    # ==========================================================
    # Utilities
    # ==========================================================

    @staticmethod
    def _hash_text(text: str, tenant_id: Optional[str] = None) -> str:
        """
        Tenant-aware hash prevents cross-tenant leakage.
        """
        base = f"{tenant_id or ''}:{text}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @classmethod
    def _is_expired(cls, timestamp: float) -> bool:
        return (time.time() - timestamp) > cls.TTL_SECONDS

    # ==========================================================
    # GET
    # ==========================================================

    @classmethod
    def get(
        cls,
        text: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[float]]:

        if not cls.ENABLED:
            return None

        key = cls._hash_text(text, tenant_id)

        with cls._lock:
            item = cls._cache.get(key)

            if not item:
                cls._misses += 1
                return None

            embedding, timestamp = item

            if cls._is_expired(timestamp):
                cls._cache.pop(key, None)
                cls._misses += 1
                return None

            cls._cache.move_to_end(key)
            cls._hits += 1
            return embedding

    # ==========================================================
    # SET
    # ==========================================================

    @classmethod
    def set(
        cls,
        text: str,
        embedding: List[float],
        tenant_id: Optional[str] = None
    ) -> None:

        if not cls.ENABLED:
            return

        key = cls._hash_text(text, tenant_id)

        with cls._lock:
            cls._cache[key] = (embedding, time.time())
            cls._cache.move_to_end(key)

            # LRU size enforcement
            while len(cls._cache) > cls.MAX_SIZE:
                cls._cache.popitem(last=False)

            # Memory cap enforcement (if enabled)
            if cls.MAX_MEMORY_MB > 0:
                while cls._estimate_memory_mb() > cls.MAX_MEMORY_MB:
                    cls._cache.popitem(last=False)

    # ==========================================================
    # Expired Cleanup
    # ==========================================================

    @classmethod
    def prune_expired(cls) -> int:
        """
        Remove expired items manually.
        Returns number removed.
        """
        removed = 0
        now = time.time()

        with cls._lock:
            keys = [
                k for k, (_, ts) in cls._cache.items()
                if (now - ts) > cls.TTL_SECONDS
            ]

            for k in keys:
                cls._cache.pop(k, None)
                removed += 1

        return removed

    # ==========================================================
    # Clear Cache
    # ==========================================================

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._cache.clear()
            cls._hits = 0
            cls._misses = 0

    # ==========================================================
    # Stats
    # ==========================================================

    @classmethod
    def stats(cls) -> Dict[str, float]:
        with cls._lock:
            total = cls._hits + cls._misses
            hit_ratio = (cls._hits / total) if total > 0 else 0.0

            return {
                "enabled": cls.ENABLED,
                "size": len(cls._cache),
                "max_size": cls.MAX_SIZE,
                "ttl_seconds": cls.TTL_SECONDS,
                "hits": cls._hits,
                "misses": cls._misses,
                "hit_ratio": round(hit_ratio, 4),
                "memory_estimate_mb": round(cls._estimate_memory_mb(), 4),
                "max_memory_mb": cls.MAX_MEMORY_MB,
            }

    # ==========================================================
    # Accurate Memory Estimation
    # ==========================================================

    @classmethod
    def _estimate_memory_mb(cls) -> float:
        total_bytes = 0

        for key, (embedding, _) in cls._cache.items():
            total_bytes += sys.getsizeof(key)

            # Estimate embedding size properly
            total_bytes += sys.getsizeof(embedding)
            for value in embedding:
                total_bytes += sys.getsizeof(value)

        return total_bytes / (1024 * 1024)

    # ==========================================================
    # Preload Support
    # ==========================================================

    @classmethod
    def preload(
        cls,
        items: Dict[str, List[float]],
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Preload known embeddings (system prompts, policies).
        """
        for text, embedding in items.items():
            cls.set(text, embedding, tenant_id)

    # ==========================================================
    # Health Check
    # ==========================================================

    @classmethod
    def health(cls) -> Dict[str, str]:
        """
        Quick health snapshot for monitoring.
        """
        return {
            "status": "enabled" if cls.ENABLED else "disabled",
            "items": str(len(cls._cache)),
            "memory_mb": str(round(cls._estimate_memory_mb(), 3)),
        }