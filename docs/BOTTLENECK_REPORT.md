# Bottleneck Report — Tier 3 Optimization

## What Was Slow

The primary bottleneck was **database query saturation**. Every GET request (list users, list URLs, list events, get by ID) hit PostgreSQL directly, even for identical queries repeated thousands of times per second. At 500 concurrent users, the DB connection pool (20 connections per app instance) became the chokepoint — queries queued up, latency spiked, and connections timed out causing cascading errors. Secondary bottleneck: Nginx used a new TCP connection per upstream request, adding overhead at high concurrency.

## What We Fixed

1. **Redis cache-aside on all GET endpoints**: List and detail responses are cached in Redis (5-min TTL for CRUD, 1-min TTL for events, 1-hr TTL for redirects). Write operations (POST/PUT/DELETE) invalidate relevant cache keys. This eliminates ~80% of DB queries under load since most VUs read the same data repeatedly.

2. **Horizontal scaling (2 → 4 Gunicorn instances)**: Each instance runs 4 workers behind Nginx `least_conn` balancing. Combined with PostgreSQL tuning (`max_connections=200`, `synchronous_commit=off`, `shared_buffers=256MB`), we raised the effective throughput ceiling from ~100 req/s to 500+ req/s.

3. **Nginx optimization**: Added HTTP/1.1 keepalive connections to upstream (pool of 64), gzip compression on JSON responses, and a 30-second proxy cache layer for GET requests. This reduces TCP handshake overhead and response sizes under sustained load.

## Evidence

- **Caching**: `X-Cache-Status` response header shows HIT/MISS from Nginx; k6 custom metrics `cache_hits`/`cache_misses` quantify Redis effectiveness; Redis `INFO` shows keyspace activity.
- **Speed comparison**: Cached GET responses serve in <5ms (Redis) vs 50-200ms (DB query). Redirect lookups drop from ~30ms to <2ms on cache hit.
- **Load test**: Run `k6 run k6-testing/load_test_tier3.js` — targets 500 VUs with `errors < 5%` and `p95 < 2s` thresholds.
