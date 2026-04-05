# Failure Modes

Documents what happens when each part of the service breaks and how the system responds.

---

## 1. Database Goes Down

**Symptom:** PostgreSQL is unreachable or crashes.

**What happens:**
- `GET /health` returns HTTP 503 with `{"status": "degraded", "db": "<error>", "cache": "ok"}`
- All endpoints that read/write URLs (`/shorten`, `/<code>`, `/api/links`, etc.) return HTTP 500 with `{"error": "internal server error"}`
- Redirects fail — users see a JSON error instead of being forwarded

**Recovery:** When PostgreSQL restarts, the connection pool reconnects automatically on the next request. No manual restart of the app is needed.

---

## 2. Redis Goes Down

**Symptom:** Redis is unreachable.

**What happens:**
- `GET /health` returns HTTP 200 — Redis is non-critical, `cache` field shows the error string
- Redirects (`GET /<code>`) fall through to the database automatically — the app catches Redis exceptions and degrades gracefully
- Cache-aside logic skips caching on write failure
- Cache invalidation on update/delete silently skips — no crash

**Impact:** Slightly slower redirects (DB hit on every request instead of cache). No data loss.

**Recovery:** When Redis restarts, caching resumes automatically on the next redirect.

---

## 3. App Process Is Killed

**Symptom:** The Flask process crashes or is manually killed (`docker kill <container>`).

**What happens:**
- All in-flight requests are dropped
- The container exits

**Recovery:** `docker-compose.yml` sets `restart: always` on the `app` service. Docker automatically restarts the container within seconds.

**Demo:**
```bash
# Start the stack
docker compose up -d

# Kill the app container
docker kill metahackathon-app-1

# Watch it resurrect (within ~5 seconds)
docker ps
```

---

## 4. Bad Input from Clients

**Symptom:** Client sends malformed JSON, missing fields, or invalid URLs.

**What happens:**

| Scenario | Status | Response |
|---|---|---|
| `POST /shorten` with no URL | 400 | `{"error": "url is required"}` |
| `POST /shorten` with invalid scheme | 400 | `{"error": "url must start with http:// or https://"}` |
| Route does not exist | 404 | `{"error": "not found"}` |
| Wrong HTTP method | 405 | `{"error": "method not allowed"}` |
| Unhandled server exception | 500 | `{"error": "internal server error"}` |

No crash, no stack trace exposed to the client.

**Demo:**
```bash
curl -s -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{}' | jq
# {"error": "url is required"}

curl -s -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "javascript:alert(1)"}' | jq
# {"error": "url must start with http:// or https://"}
```

---

## 5. Short Code Collision

**Symptom:** `_generate_short_code()` produces a code that already exists in the DB.

**What happens:**
- `POST /shorten` detects the collision via a DB existence check
- Retries generation in a loop until a unique code is found
- Extremely unlikely in practice (base62^7 ≈ 3.5 trillion combinations)

---

## 6. Duplicate URL Shortening

**Symptom:** The same original URL is submitted to `POST /shorten` twice.

**What happens:**
- First request → `201 Created` with a new `short_code`
- Second request → `200 OK` with the **same** `short_code` (dedup)
- If the link was deleted before the second request → `201 Created` with a **new** `short_code`

---

## 7. Click Logging Failure

**Symptom:** The background thread that logs click events to the DB throws an exception.

**What happens:**
- The exception is caught silently — the redirect still succeeds
- Click counts may be under-reported but the user is never affected

---

## 8. Stale Cache After Link Update/Delete

**Symptom:** A link is updated or deleted, but the Redis TTL hasn't expired yet.

**What happens:**
- `PUT` and `DELETE` both call `cache.delete(f"url:{code}")` to invalidate immediately
- If the cache delete fails (Redis down), the stale entry expires naturally after 1 hour (TTL)
- During that window, deleted links could still redirect — mitigated by Redis health recovery described above
