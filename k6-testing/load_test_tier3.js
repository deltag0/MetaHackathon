import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------
const errorRate = new Rate("errors");
const cacheHits = new Counter("cache_hits");
const cacheMisses = new Counter("cache_misses");
const readLatency = new Trend("read_latency", true);
const writeLatency = new Trend("write_latency", true);
const redirectLatency = new Trend("redirect_latency", true);

// ---------------------------------------------------------------------------
// Configuration — Tier 3 Gold: 500 concurrent users
// ---------------------------------------------------------------------------
const BASE_URL = __ENV.BASE_URL || "http://localhost";

export const options = {
  scenarios: {
    tsunami: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 250 },  // ramp to 250
        { duration: "30s", target: 500 },  // ramp to 500
        { duration: "2m",  target: 500 },  // hold the tsunami
        { duration: "15s", target: 0 },    // ramp down
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"],  // p95 under 2s
    errors: ["rate<0.05"],              // less than 5% errors
    http_req_failed: ["rate<0.05"],     // built-in failure rate < 5%
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const headers = { "Content-Type": "application/json" };

function checkResponse(res, name, expectedStatus) {
  const passed = check(res, {
    [`${name} status ${expectedStatus}`]: (r) => r.status === expectedStatus,
  });
  errorRate.add(!passed);
  return passed;
}

function trackCacheStatus(res) {
  const cacheHeader = res.headers["X-Cache-Status"];
  if (cacheHeader === "HIT") {
    cacheHits.add(1);
  } else {
    cacheMisses.add(1);
  }
}

// ---------------------------------------------------------------------------
// Scenario: each VU cycles through CRUD + caching verification
// Uses URL grouping (tags.name) to avoid high-cardinality metric explosion
// ---------------------------------------------------------------------------
export default function () {
  // ---- USERS ----

  // List users (cached)
  let res = http.get(`${BASE_URL}/users?page=1&per_page=10`);
  readLatency.add(res.timings.duration);
  checkResponse(res, "GET /users", 200);
  trackCacheStatus(res);

  // Create a user
  const email = `lt_${__VU}_${__ITER}_${Date.now()}@t.co`;
  res = http.post(
    `${BASE_URL}/users`,
    JSON.stringify({ email }),
    { headers }
  );
  writeLatency.add(res.timings.duration);
  const userCreated = checkResponse(res, "POST /users", 201);

  let userId = null;
  if (userCreated && res.json()) {
    userId = res.json().id;
  }

  // Get user by ID
  if (userId) {
    res = http.get(`${BASE_URL}/users/${userId}`, {
      tags: { name: "GET /users/:id" },
    });
    readLatency.add(res.timings.duration);
    checkResponse(res, "GET /users/:id", 200);
  }

  // Update user
  if (userId) {
    res = http.put(
      `${BASE_URL}/users/${userId}`,
      JSON.stringify({ email: `u_${__VU}_${Date.now()}@t.co` }),
      { headers, tags: { name: "PUT /users/:id" } }
    );
    writeLatency.add(res.timings.duration);
    checkResponse(res, "PUT /users/:id", 200);
  }

  sleep(0.05);

  // ---- URLS ----

  // List URLs (cached)
  res = http.get(`${BASE_URL}/urls?is_active=true&limit=20`);
  readLatency.add(res.timings.duration);
  checkResponse(res, "GET /urls", 200);
  trackCacheStatus(res);

  // Create a URL
  res = http.post(
    `${BASE_URL}/urls`,
    JSON.stringify({
      original_url: `https://example.com/t3-${__VU}-${__ITER}-${Date.now()}`,
      title: `T3 URL ${__VU}`,
      user_id: userId || 1,
    }),
    { headers }
  );
  writeLatency.add(res.timings.duration);
  const urlCreated = checkResponse(res, "POST /urls", 201);

  let urlId = null;
  let shortCode = null;
  if (urlCreated && res.json()) {
    urlId = res.json().id;
    shortCode = res.json().short_code;
  }

  // Get URL by ID (cached)
  if (urlId) {
    res = http.get(`${BASE_URL}/urls/${urlId}`, {
      tags: { name: "GET /urls/:id" },
    });
    readLatency.add(res.timings.duration);
    checkResponse(res, "GET /urls/:id", 200);
  }

  // Test short URL redirect (the core caching path)
  if (shortCode) {
    res = http.get(`${BASE_URL}/${shortCode}`, {
      redirects: 0,
      tags: { name: "GET /:code (redirect)" },
    });
    redirectLatency.add(res.timings.duration);
    check(res, {
      "redirect status 302": (r) => r.status === 302,
    });

    // Second hit — should come from Redis cache
    res = http.get(`${BASE_URL}/${shortCode}`, {
      redirects: 0,
      tags: { name: "GET /:code (cached redirect)" },
    });
    redirectLatency.add(res.timings.duration);
    check(res, {
      "cached redirect 302": (r) => r.status === 302,
    });
  }

  sleep(0.05);

  // ---- EVENTS ----

  // List events (cached, limited)
  res = http.get(`${BASE_URL}/events?event_type=click&limit=20`);
  readLatency.add(res.timings.duration);
  checkResponse(res, "GET /events", 200);
  trackCacheStatus(res);

  // Create an event
  let eventId = null;
  if (urlId) {
    res = http.post(
      `${BASE_URL}/events`,
      JSON.stringify({
        url_id: urlId,
        user_id: userId || 1,
        event_type: "click",
        details: { source: "tier3" },
      }),
      { headers }
    );
    writeLatency.add(res.timings.duration);
    const eventCreated = checkResponse(res, "POST /events", 201);
    if (eventCreated && res.json()) {
      eventId = res.json().id;
    }
  }

  sleep(0.05);

  // ---- CLEANUP (correct order: events → urls → users) ----

  // Delete event first (no FK dependents)
  if (eventId) {
    res = http.del(`${BASE_URL}/events/${eventId}`, {
      tags: { name: "DELETE /events/:id" },
    });
    writeLatency.add(res.timings.duration);
    checkResponse(res, "DELETE /events/:id", 200);
  }

  // Delete URL (now safe — event is gone)
  if (urlId) {
    res = http.del(`${BASE_URL}/urls/${urlId}`, {
      tags: { name: "DELETE /urls/:id" },
    });
    writeLatency.add(res.timings.duration);
    checkResponse(res, "DELETE /urls/:id", 200);
  }

  // Delete user last (now safe — URL is gone)
  if (userId) {
    res = http.del(`${BASE_URL}/users/${userId}`, {
      tags: { name: "DELETE /users/:id" },
    });
    writeLatency.add(res.timings.duration);
    checkResponse(res, "DELETE /users/:id", 200);
  }
}
