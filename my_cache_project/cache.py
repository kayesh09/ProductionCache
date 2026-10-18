from __future__ import annotations
import time
import threading
from typing import Any, Optional, Dict


class _CacheEntry:
    """Internal representation of a cache item."""
    __slots__ = ('key', 'value', 'expires_at', 'prev', 'next')

    def __init__(self, key: str, value: Any, expires_at: Optional[float]):
        self.key = key
        self.value = value
        self.expires_at = expires_at  # monotonic timestamp, None if no expiration
        self.prev: Optional[_CacheEntry] = None
        self.next: Optional[_CacheEntry] = None

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        return self.expires_at is not None and time.monotonic() >= self.expires_at


class _DoublyLinkedList:
    """Doubly linked list to maintain LRU order. 

    Head represents Most Recently Used (MRU), Tail represents Least Recently Used (LRU).
    """

    def __init__(self):
        self.head = _CacheEntry("", None, None)  # Dummy head
        self.tail = _CacheEntry("", None, None)  # Dummy tail
        self.head.next = self.tail
        self.tail.prev = self.head

    def add_to_head(self, entry: _CacheEntry) -> None:
        """Add an entry right after the dummy head (MRU position)."""
        entry.next = self.head.next
        entry.prev = self.head
        self.head.next.prev = entry
        self.head.next = entry

    def remove_entry(self, entry: _CacheEntry) -> None:
        """Remove a specific entry from the list."""
        entry.prev.next = entry.next
        entry.next.prev = entry.prev

    def move_to_head(self, entry: _CacheEntry) -> None:
        """Move an existing entry to the MRU position."""
        self.remove_entry(entry)
        self.add_to_head(entry)

    def pop_tail(self) -> _CacheEntry:
        """Remove and return the LRU entry (right before the dummy tail)."""
        lru_entry = self.tail.prev
        self.remove_entry(lru_entry)
        return lru_entry


class ProductionCache:
    """
    Thread-safe in-memory cache with TTL, max size, and LRU eviction.
    """

    def __init__(self, max_size: int = 1000):
        if not (1 <= max_size <= 100_000):
            raise ValueError("max_size must be between 1 and 100,000")

        self.max_size = max_size
        self._cache: Dict[str, _CacheEntry] = {}
        self._lru = _DoublyLinkedList()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_count": 0
        }

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Insert or update a key-value pair in the cache."""
        with self._lock:
            # time.monotonic() is used to prevent issues with system clock changes
            expires_at = time.monotonic() + ttl if ttl is not None else None

            if key in self._cache:
                # Update existing entry
                entry = self._cache[key]
                entry.value = value
                entry.expires_at = expires_at
                self._lru.move_to_head(entry)
            else:
                # Evict if necessary before inserting a new item
                if len(self._cache) >= self.max_size:
                    self._evict_one()

                entry = _CacheEntry(key, value, expires_at)
                self._cache[key] = entry
                self._lru.add_to_head(entry)

    def get(self, key: str) -> Any | None:
        """Retrieve a value by key. Returns None if missing or expired."""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            # Lazy expiration check
            if entry.is_expired():
                self._remove_entry(entry)
                self._stats["misses"] += 1
                self._stats["expired_count"] += 1
                return None

            # Cache hit: update LRU position
            self._lru.move_to_head(entry)
            self._stats["hits"] += 1
            return entry.value

    def delete(self, key: str) -> bool:
        """Manually remove a key. Returns True if key existed, False otherwise."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(self._cache[key])
                return True
            return False

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._lru = _DoublyLinkedList()

    def get_stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            return self._stats.copy()

    def _remove_entry(self, entry: _CacheEntry) -> None:
        """Internal method to remove an entry from both dict and LRU list."""
        self._lru.remove_entry(entry)
        del self._cache[entry.key]

    def _evict_one(self) -> None:
        """Evict the least recently used non-expired item.

        If the LRU item is expired, it is removed and counted as expired_count.
        We continue checking until we evict a non-expired item or the cache drops 
        below max_size.
        """
        while len(self._cache) >= self.max_size:
            lru_entry = self._lru.tail.prev

            # Safety check: should never happen if max_size >= 1
            if lru_entry == self._lru.head:
                break

            if lru_entry.is_expired():
                self._remove_entry(lru_entry)
                self._stats["expired_count"] += 1
            else:
                self._remove_entry(lru_entry)
                self._stats["evictions"] += 1
                break  # Successfully evicted a non-expired item