import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------
const errorRate = new Rate("errors");
const usersLatency = new Trend("users_latency", true);
const urlsLatency = new Trend("urls_latency", true);
const eventsLatency = new Trend("events_latency", true);

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
// For Tier 2 the BASE_URL points at the Nginx load balancer (default: port 80)
const BASE_URL = __ENV.BASE_URL || "http://localhost";

export const options = {
  // ---- Tier 2 Silver: 200 concurrent users ----
  scenarios: {
    ramp_up: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 100 }, // ramp to 100
        { duration: "30s", target: 200 }, // ramp to 200
        { duration: "1m", target: 200 },  // hold at 200
        { duration: "15s", target: 0 },   // ramp down
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<3000"], // p95 under 3 seconds
    errors: ["rate<0.5"],              // less than 50% errors
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

// ---------------------------------------------------------------------------
// Scenario: each VU cycles through all three resource endpoints
// ---------------------------------------------------------------------------
export default function () {
  // ---- USERS ----

  // List users
  let res = http.get(`${BASE_URL}/users`);
  usersLatency.add(res.timings.duration);
  checkResponse(res, "GET /users", 200);

  // Create a user
  const email = `loadtest_${__VU}_${__ITER}_${Date.now()}@test.com`;
  res = http.post(
    `${BASE_URL}/users`,
    JSON.stringify({ email: email }),
    { headers }
  );
  usersLatency.add(res.timings.duration);
  const userCreated = checkResponse(res, "POST /users", 201);

  let userId = null;
  if (userCreated && res.json()) {
    userId = res.json().id;
  }

  // Get user by ID
  if (userId) {
    res = http.get(`${BASE_URL}/users/${userId}`);
    usersLatency.add(res.timings.duration);
    checkResponse(res, "GET /users/:id", 200);
  }

  // Update user
  if (userId) {
    res = http.put(
      `${BASE_URL}/users/${userId}`,
      JSON.stringify({ email: `updated_${__VU}_${__ITER}_${Date.now()}@test.com` }),
      { headers }
    );
    usersLatency.add(res.timings.duration);
    checkResponse(res, "PUT /users/:id", 200);
  }

  // Paginated list
  res = http.get(`${BASE_URL}/users?page=1&per_page=10`);
  usersLatency.add(res.timings.duration);
  checkResponse(res, "GET /users?page", 200);

  sleep(0.1);

  // ---- URLS ----

  // List URLs
  res = http.get(`${BASE_URL}/urls`);
  urlsLatency.add(res.timings.duration);
  checkResponse(res, "GET /urls", 200);

  // Create a URL
  res = http.post(
    `${BASE_URL}/urls`,
    JSON.stringify({
      original_url: `https://example.com/load-test-${__VU}-${__ITER}-${Date.now()}`,
      title: `Load Test URL ${__VU}`,
      user_id: userId || 1,
    }),
    { headers }
  );
  urlsLatency.add(res.timings.duration);
  const urlCreated = checkResponse(res, "POST /urls", 201);

  let urlId = null;
  if (urlCreated && res.json()) {
    urlId = res.json().id;
  }

  // Get URL by ID
  if (urlId) {
    res = http.get(`${BASE_URL}/urls/${urlId}`);
    urlsLatency.add(res.timings.duration);
    checkResponse(res, "GET /urls/:id", 200);
  }

  // Update URL
  if (urlId) {
    res = http.put(
      `${BASE_URL}/urls/${urlId}`,
      JSON.stringify({ title: "Updated Load Test Title" }),
      { headers }
    );
    urlsLatency.add(res.timings.duration);
    checkResponse(res, "PUT /urls/:id", 200);
  }

  // Filter by active
  res = http.get(`${BASE_URL}/urls?is_active=true`);
  urlsLatency.add(res.timings.duration);
  checkResponse(res, "GET /urls?is_active", 200);

  sleep(0.1);

  // ---- EVENTS ----

  // List events
  res = http.get(`${BASE_URL}/events`);
  eventsLatency.add(res.timings.duration);
  checkResponse(res, "GET /events", 200);

  // Create an event
  if (urlId) {
    res = http.post(
      `${BASE_URL}/events`,
      JSON.stringify({
        url_id: urlId,
        user_id: userId || 1,
        event_type: "click",
        details: { referrer: "https://google.com", source: "load_test_tier2" },
      }),
      { headers }
    );
    eventsLatency.add(res.timings.duration);
    checkResponse(res, "POST /events", 201);
  }

  // Filter events by type
  res = http.get(`${BASE_URL}/events?event_type=click`);
  eventsLatency.add(res.timings.duration);
  checkResponse(res, "GET /events?event_type", 200);

  // Filter events by url_id
  if (urlId) {
    res = http.get(`${BASE_URL}/events?url_id=${urlId}`);
    eventsLatency.add(res.timings.duration);
    checkResponse(res, "GET /events?url_id", 200);
  }

  sleep(0.1);

  // ---- CLEANUP ----
  if (urlId) {
    res = http.del(`${BASE_URL}/urls/${urlId}`);
    urlsLatency.add(res.timings.duration);
    checkResponse(res, "DELETE /urls/:id", 200);
  }

  if (userId) {
    res = http.del(`${BASE_URL}/users/${userId}`);
    usersLatency.add(res.timings.duration);
    checkResponse(res, "DELETE /users/:id", 200);
  }
}

// ---------------------------------------------------------------------------
// Summary: k6 prints this automatically, includes p95, error rate, etc.
// ---------------------------------------------------------------------------
