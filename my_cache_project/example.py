import time
from cache import InMemoryCache


def main():
    print("--- Initializing Cache ---")
    # Max size 3, default TTL 5 seconds, cleanup every 1 second
    cache = InMemoryCache(max_size=3, default_ttl_ms=5000, cleanup_interval_ms=1000)

    print("\n--- Basic Operations ---")
    cache.set("user:1", {"name": "Alice"})
    cache.set("user:2", {"name": "Bob"}, ttl_ms=1000)  # Overrides default, expires in 1s

    print(f"Get user:1: {cache.get('user:1')}")  # Hit
    print(f"Get user:2: {cache.get('user:2')}")  # Hit

    time.sleep(1.5)
    print("\n--- After 1.5 seconds ---")
    print(f"Get user:1: {cache.get('user:1')}")  # Hit (Still valid, default 5s TTL)
    print(f"Get user:2: {cache.get('user:2')}")  # Miss (Expired after 1s)

    print("\n--- LRU Eviction ---")
    cache.set("user:3", "Charlie")
    cache.set("user:4", "Dave")
    # Cache is now full: user:1, user:3, user:4
    # Add one more to trigger eviction
    cache.set("user:5", "Eve")
    print(f"Get user:1 (Should be evicted): {cache.get('user:1')}")  # Miss (Evicted)
    print(f"Get user:5: {cache.get('user:5')}")  # Hit

    print("\n--- Statistics ---")
    stats = cache.get_stats()
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Evictions: {stats['evictions']}")

    print("\n--- Graceful Shutdown ---")
    cache.stop()
    print("Cache background thread stopped successfully.")


if __name__ == "__main__":
    main()