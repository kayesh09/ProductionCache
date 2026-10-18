import pytest
import time
import threading
from cache import ProductionCache


def test_basic_set_get():
    cache = ProductionCache(max_size=10)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_missing_key():
    cache = ProductionCache(max_size=10)
    assert cache.get("b") is None
    stats = cache.get_stats()
    assert stats["misses"] == 1


def test_delete_existing():
    cache = ProductionCache(max_size=10)
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.get("a") is None


def test_delete_non_existing():
    cache = ProductionCache(max_size=10)
    assert cache.delete("a") is False


def test_overwrite_key():
    cache = ProductionCache(max_size=10)
    cache.set("a", 1)
    cache.set("a", 2)
    assert cache.get("a") == 2
    # Ensure size didn't increase
    assert len(cache._cache) == 1


def test_ttl_expiration():
    cache = ProductionCache(max_size=10)
    cache.set("temp", 1, ttl=0.1)
    time.sleep(0.2)
    assert cache.get("temp") is None

    stats = cache.get_stats()
    assert stats["misses"] == 1
    assert stats["expired_count"] == 1


def test_lru_eviction():
    cache = ProductionCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)

    # Access "a" to make it MRU
    cache.get("a")

    # Insert "c", should evict "b" (LRU)
    cache.set("c", 3)

    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("c") == 3

    stats = cache.get_stats()
    assert stats["evictions"] == 1


def test_evict_non_expired_skips_expired():
    """Ensure eviction removes expired items first instead of evicting non-expired ones."""
    cache = ProductionCache(max_size=2)
    cache.set("a", 1, ttl=0.1)  # will expire
    cache.set("b", 2)  # will not expire

    time.sleep(0.2)

    # "a" is expired but still in cache.
    # Adding "c" should remove "a" (expired), not "b" (LRU non-expired)
    cache.set("c", 3)

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3

    stats = cache.get_stats()
    assert stats["evictions"] == 0
    assert stats["expired_count"] == 1


def test_max_size_1():
    cache = ProductionCache(max_size=1)
    cache.set("a", 1)
    assert cache.get("a") == 1
    cache.set("b", 2)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    stats = cache.get_stats()
    assert stats["evictions"] == 1


def test_thread_safety():
    cache = ProductionCache(max_size=1000)

    def worker():
        for i in range(500):
            cache.set(f"key_{i}", i, ttl=0.05)
            cache.get(f"key_{i}")
            cache.delete(f"key_{i}")

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # If it completes without deadlock or crashing, it's successful
    stats = cache.get_stats()
    assert stats["hits"] > 0
    assert stats["misses"] > 0


def test_metrics_accuracy():
    cache = ProductionCache(max_size=3)
    cache.set("a", 1)
    cache.set("b", 2, ttl=0.1)

    cache.get("a")  # hit
    cache.get("b")  # hit
    cache.get("c")  # miss

    time.sleep(0.2)
    cache.get("b")  # miss + expired

    cache.set("d", 4)
    cache.set("e", 5)
    cache.set("f", 6)  # should evict "a"

    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 2
    assert stats["expired_count"] == 1
    assert stats["evictions"] == 1


def test_clear():
    cache = ProductionCache(max_size=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None
    # Stats should persist after clear
    stats = cache.get_stats()
    assert stats["misses"] == 2


def test_invalid_max_size():
    with pytest.raises(ValueError):
        ProductionCache(max_size=0)
    with pytest.raises(ValueError):
        ProductionCache(max_size=100_001)


def test_ttl_none_never_expires():
    cache = ProductionCache(max_size=10)
    cache.set("forever", 1, ttl=None)
    # Can't wait forever, but we can ensure it doesn't expire immediately
    assert cache.get("forever") == 1