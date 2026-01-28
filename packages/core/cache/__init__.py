"""Caching layer for query results and embeddings."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """A cached item."""

    key: str
    value: Any
    created_at: float = Field(default_factory=time.time)
    expires_at: float | None = None
    hit_count: int = 0
    last_accessed: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CacheStats(BaseModel):
    """Cache statistics."""

    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    hit_rate: float = 0.0
    memory_estimate_mb: float = 0.0
    oldest_entry: str | None = None
    newest_entry: str | None = None


class CacheManager:
    """In-memory cache with persistence for expensive operations."""

    def __init__(
        self,
        storage_path: str | None = None,
        default_ttl_seconds: int = 3600,  # 1 hour
        max_entries: int = 10000,
    ):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "cache"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries

        # In-memory caches
        self._query_cache: dict[str, CacheEntry] = {}
        self._embedding_cache: dict[str, CacheEntry] = {}
        self._response_cache: dict[str, CacheEntry] = {}

        # Stats
        self._hits = 0
        self._misses = 0

        # Load persisted cache
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self.storage_path / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    now = time.time()

                    # Load query cache
                    for key, entry_data in data.get("query_cache", {}).items():
                        entry = CacheEntry(**entry_data)
                        if entry.expires_at is None or entry.expires_at > now:
                            self._query_cache[key] = entry

                    # Load response cache
                    for key, entry_data in data.get("response_cache", {}).items():
                        entry = CacheEntry(**entry_data)
                        if entry.expires_at is None or entry.expires_at > now:
                            self._response_cache[key] = entry
            except Exception:
                pass

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        cache_file = self.storage_path / "cache.json"
        data = {
            "query_cache": {k: v.model_dump() for k, v in self._query_cache.items()},
            "response_cache": {k: v.model_dump() for k, v in self._response_cache.items()},
        }
        with open(cache_file, "w") as f:
            json.dump(data, f)

    def _make_key(self, *args: Any) -> str:
        """Generate a cache key from arguments."""
        key_str = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def _evict_if_needed(self, cache: dict[str, CacheEntry]) -> None:
        """Evict old entries if cache is full."""
        if len(cache) >= self.max_entries:
            # Remove expired entries first
            now = time.time()
            expired = [k for k, v in cache.items() if v.expires_at and v.expires_at < now]
            for key in expired:
                del cache[key]

            # If still full, remove least recently used
            if len(cache) >= self.max_entries:
                sorted_entries = sorted(cache.items(), key=lambda x: x[1].last_accessed)
                to_remove = len(cache) - self.max_entries + 100  # Remove 100 extra
                for key, _ in sorted_entries[:to_remove]:
                    del cache[key]

    # =========================================================================
    # Query Cache (for repeated user queries)
    # =========================================================================

    def get_query_response(
        self,
        query: str,
        agent_id: str,
    ) -> dict[str, Any] | None:
        """Get a cached response for a query."""
        key = self._make_key(query.lower().strip(), agent_id)
        entry = self._query_cache.get(key)

        if entry:
            now = time.time()
            if entry.expires_at is None or entry.expires_at > now:
                entry.hit_count += 1
                entry.last_accessed = now
                self._hits += 1
                return entry.value
            else:
                # Expired
                del self._query_cache[key]

        self._misses += 1
        return None

    def set_query_response(
        self,
        query: str,
        agent_id: str,
        response: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache a query response."""
        key = self._make_key(query.lower().strip(), agent_id)
        ttl = ttl_seconds or self.default_ttl

        self._evict_if_needed(self._query_cache)

        self._query_cache[key] = CacheEntry(
            key=key,
            value=response,
            expires_at=time.time() + ttl,
            metadata={"query": query[:100], "agent_id": agent_id},
        )
        self._save_cache()

    # =========================================================================
    # Embedding Cache (for document chunks)
    # =========================================================================

    def get_embedding(self, text: str) -> list[float] | None:
        """Get a cached embedding."""
        key = self._make_key(text)
        entry = self._embedding_cache.get(key)

        if entry:
            now = time.time()
            if entry.expires_at is None or entry.expires_at > now:
                entry.hit_count += 1
                entry.last_accessed = now
                self._hits += 1
                return entry.value

        self._misses += 1
        return None

    def set_embedding(
        self,
        text: str,
        embedding: list[float],
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache an embedding."""
        key = self._make_key(text)
        ttl = ttl_seconds or (self.default_ttl * 24)  # Embeddings cache longer

        self._evict_if_needed(self._embedding_cache)

        self._embedding_cache[key] = CacheEntry(
            key=key,
            value=embedding,
            expires_at=time.time() + ttl if ttl else None,
        )

    # =========================================================================
    # Response Cache (for LLM responses)
    # =========================================================================

    def get_llm_response(
        self,
        prompt: str,
        system: str | None = None,
        model: str = "default",
    ) -> str | None:
        """Get a cached LLM response."""
        key = self._make_key(prompt, system, model)
        entry = self._response_cache.get(key)

        if entry:
            now = time.time()
            if entry.expires_at is None or entry.expires_at > now:
                entry.hit_count += 1
                entry.last_accessed = now
                self._hits += 1
                return entry.value

        self._misses += 1
        return None

    def set_llm_response(
        self,
        prompt: str,
        response: str,
        system: str | None = None,
        model: str = "default",
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache an LLM response."""
        key = self._make_key(prompt, system, model)
        ttl = ttl_seconds or self.default_ttl

        self._evict_if_needed(self._response_cache)

        self._response_cache[key] = CacheEntry(
            key=key,
            value=response,
            expires_at=time.time() + ttl,
            metadata={"model": model},
        )
        self._save_cache()

    # =========================================================================
    # Cache Management
    # =========================================================================

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        total = len(self._query_cache) + len(self._embedding_cache) + len(self._response_cache)
        total_requests = self._hits + self._misses

        # Estimate memory usage
        memory_mb = 0.0
        for cache in [self._query_cache, self._embedding_cache, self._response_cache]:
            for entry in cache.values():
                memory_mb += len(json.dumps(entry.value, default=str)) / (1024 * 1024)

        # Find oldest/newest
        all_entries = list(self._query_cache.values()) + list(self._response_cache.values())
        oldest = min((e.created_at for e in all_entries), default=None)
        newest = max((e.created_at for e in all_entries), default=None)

        return CacheStats(
            total_entries=total,
            total_hits=self._hits,
            total_misses=self._misses,
            hit_rate=(self._hits / total_requests * 100) if total_requests > 0 else 0.0,
            memory_estimate_mb=memory_mb,
            oldest_entry=datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            newest_entry=datetime.fromtimestamp(newest).isoformat() if newest else None,
        )

    def clear_cache(self, cache_type: str | None = None) -> int:
        """Clear cache entries."""
        count = 0
        if cache_type is None or cache_type == "query":
            count += len(self._query_cache)
            self._query_cache.clear()
        if cache_type is None or cache_type == "embedding":
            count += len(self._embedding_cache)
            self._embedding_cache.clear()
        if cache_type is None or cache_type == "response":
            count += len(self._response_cache)
            self._response_cache.clear()

        self._save_cache()
        return count

    def invalidate_agent_cache(self, agent_id: str) -> int:
        """Invalidate all cache entries for an agent."""
        count = 0

        # Clear query cache for agent
        keys_to_remove = [
            k for k, v in self._query_cache.items()
            if v.metadata.get("agent_id") == agent_id
        ]
        for key in keys_to_remove:
            del self._query_cache[key]
            count += 1

        self._save_cache()
        return count


# Singleton instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the cache manager singleton."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


__all__ = [
    "CacheEntry",
    "CacheStats",
    "CacheManager",
    "get_cache_manager",
]
