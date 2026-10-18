.

🚀 ProductionCache
A highly performant, thread-safe, in-memory caching system built in Python. Engineered from scratch using a Hash Map and Doubly Linked List to guarantee O(1) time complexity for all core operations. Designed for high-concurrency backend applications requiring fast data access, automatic memory management, and observability.

✨ Key Features
O(1) Performance: Utilizes a Hash Map combined with a custom Doubly Linked List to ensure constant-time set, get, and delete operations, regardless of cache size.
Thread-Safe: Built for concurrent environments using threading.RLock. Safely handles thousands of simultaneous read/write requests without race conditions or deadlocks.
Smart LRU Eviction: Enforces a strict max_size. When capacity is reached, the cache evicts the Least Recently Used (LRU) item. Bonus: It intelligently skips expired items during eviction to preserve active data.
TTL Auto-Expiration: Supports Time-To-Live (in seconds) for automatic data expiration. Uses time.monotonic() to ensure TTL accuracy is immune to system clock drifts or NTP syncs.
Built-in Metrics: Tracks hits, misses, evictions, and expired_count for real-time observability and performance tuning.
Zero Dependencies: Built using only Python's standard library.
🏗️ Architecture & Technical Decisions
1. Data Structure: Hash Map + Doubly Linked List
To achieve O(1) time complexity for both lookups (Hash Map) and LRU ordering (Linked List), the cache combines both:

Hash Map (dict): Maps string keys to _CacheEntry objects for instant lookup.
Doubly Linked List: Maintains the chronological usage of items. The Head represents the Most Recently Used (MRU) item, and the Tail represents the Least Recently Used (LRU) item. Updating recency is just a matter of moving a node to the head.
2. Clock Immunity (time.monotonic)
Standard time functions like time.time() can jump backwards if the operating system syncs the clock via NTP. This cache uses time.monotonic(), which only ever moves forward, guaranteeing that TTLs never behave unpredictably.

3. Smart Eviction Algorithm
When max_size is reached, standard LRU caches simply delete the tail item. ProductionCache goes a step further: it checks if the LRU item is already expired. If it is, it deletes the expired item (incrementing expired_count) and checks the next item, ensuring valid data isn't evicted prematurely.

📦 Installation
No external packages are required. Simply include cache.py in your project.

To run the tests, you will need pytest:

pip install pytest
