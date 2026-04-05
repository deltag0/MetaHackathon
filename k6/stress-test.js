import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ── Custom metrics ──────────────────────────────────────────────
const errorRate = new Rate("errors");
const redirectDuration = new Trend("redirect_duration", true);
const shortenDuration = new Trend("shorten_duration", true);
const listLinksDuration = new Trend("list_links_duration", true);
const totalRequests = new Counter("total_requests");

// ── Configuration ───────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost";

// Stress test stages: ramp up → sustained peak → spike → recovery
export const options = {
  stages: [
    // Warm-up
    { duration: "30s", target: 50 },
    // Ramp to moderate load
    { duration: "1m", target: 150 },
    // Sustained moderate load
    { duration: "2m", target: 150 },
    // Ramp to heavy load
    { duration: "1m", target: 300 },
    // Sustained heavy load
    { duration: "2m", target: 300 },
    // Spike test - sudden burst
    { duration: "30s", target: 500 },
    // Hold the spike
    { duration: "1m", target: 500 },
    // Recovery
    { duration: "1m", target: 50 },
    // Cool down
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<5000"], // 95th < 2s, 99th < 5s
    errors: ["rate<0.1"], // Error rate < 10%
    redirect_duration: ["p(95)<1000"], // Redirects should be fast
    shorten_duration: ["p(95)<2000"],
    list_links_duration: ["p(95)<2000"],
  },
};

// ── Shared state ────────────────────────────────────────────────
// Pre-generated URLs to shorten (avoids duplicate detection skewing results)
function randomUrl() {
  const id = Math.random().toString(36).substring(2, 15);
  return `https://example.com/page/${id}/${Date.now()}`;
}

// Store short codes created during the test for redirect testing
const shortCodes = [];

// ── Setup: register a test user and create some initial URLs ────
export function setup() {
  const timestamp = Date.now();
  const email = `k6-stress-${timestamp}@test.com`;
  const password = "testpassword123";

  // Register
  const regRes = http.post(
    `${BASE_URL}/api/auth/register`,
    JSON.stringify({ email, password }),
    { headers: { "Content-Type": "application/json" } }
  );

  let token = "";
  let userId = null;
  if (regRes.status === 201) {
    const body = regRes.json();
    token = body.session_token;
    userId = body.user.id;
  } else {
    // Try login if already exists
    const loginRes = http.post(
      `${BASE_URL}/api/auth/login`,
      JSON.stringify({ email, password }),
      { headers: { "Content-Type": "application/json" } }
    );
    if (loginRes.status === 200) {
      const body = loginRes.json();
      token = body.session_token;
      userId = body.user.id;
    }
  }

  // Seed some URLs for redirect testing
  const seedCodes = [];
  for (let i = 0; i < 20; i++) {
    const res = http.post(
      `${BASE_URL}/shorten`,
      JSON.stringify({
        url: `https://example.com/seed/${i}/${timestamp}`,
        title: `Seed URL ${i}`,
        user_id: userId,
      }),
      { headers: { "Content-Type": "application/json" } }
    );
    if (res.status === 201 || res.status === 200) {
      try {
        seedCodes.push(res.json().short_code);
      } catch (_) {}
    }
  }

  console.log(`Setup complete: ${seedCodes.length} seed URLs created`);
  return { token, userId, seedCodes, email };
}

// ── Main test scenarios ─────────────────────────────────────────
export default function (data) {
  const { token, userId, seedCodes } = data;
  const headers = {
    "Content-Type": "application/json",
    Authorization: token ? `Bearer ${token}` : "",
  };

  // Weight the scenarios to match realistic traffic patterns:
  // ~50% redirects, ~20% shorten, ~15% list, ~10% stats, ~5% health
  const rand = Math.random();

  if (rand < 0.5) {
    // ── Redirect (the hot path) ───────────────────────────────
    group("redirect", () => {
      if (seedCodes.length === 0) return;
      const code = seedCodes[Math.floor(Math.random() * seedCodes.length)];
      const res = http.get(`${BASE_URL}/${code}`, {
        redirects: 0, // Don't follow redirect, just measure response time
      });
      redirectDuration.add(res.timings.duration);
      totalRequests.add(1);
      const ok = check(res, {
        "redirect returns 302": (r) => r.status === 302,
      });
      errorRate.add(!ok);
    });
  } else if (rand < 0.7) {
    // ── Shorten a new URL ─────────────────────────────────────
    group("shorten", () => {
      const res = http.post(
        `${BASE_URL}/shorten`,
        JSON.stringify({
          url: randomUrl(),
          title: `K6 Test ${Date.now()}`,
          user_id: userId,
        }),
        { headers }
      );
      shortenDuration.add(res.timings.duration);
      totalRequests.add(1);
      const ok = check(res, {
        "shorten returns 201": (r) => r.status === 201,
      });
      errorRate.add(!ok);

      // Save the code for redirect testing by other VUs
      if (res.status === 201) {
        try {
          const code = res.json().short_code;
          if (code && seedCodes.length < 500) {
            seedCodes.push(code);
          }
        } catch (_) {}
      }
    });
  } else if (rand < 0.85) {
    // ── List links (paginated) ────────────────────────────────
    group("list_links", () => {
      const page = Math.floor(Math.random() * 5) + 1;
      const res = http.get(`${BASE_URL}/api/links?page=${page}&per_page=20`, {
        headers,
      });
      listLinksDuration.add(res.timings.duration);
      totalRequests.add(1);
      const ok = check(res, {
        "list returns 200": (r) => r.status === 200,
      });
      errorRate.add(!ok);
    });
  } else if (rand < 0.95) {
    // ── Stats lookup ──────────────────────────────────────────
    group("stats", () => {
      if (seedCodes.length === 0) return;
      const code = seedCodes[Math.floor(Math.random() * seedCodes.length)];
      const res = http.get(`${BASE_URL}/api/links/${code}`, { headers });
      totalRequests.add(1);
      const ok = check(res, {
        "stats returns 200": (r) => r.status === 200,
      });
      errorRate.add(!ok);
    });
  } else {
    // ── Health check ──────────────────────────────────────────
    group("health", () => {
      const res = http.get(`${BASE_URL}/health/live`);
      totalRequests.add(1);
      const ok = check(res, {
        "health returns 200": (r) => r.status === 200,
      });
      errorRate.add(!ok);
    });
  }

  // Small random sleep to simulate real user think time
  sleep(Math.random() * 0.5);
}

// ── Teardown ────────────────────────────────────────────────────
export function teardown(data) {
  console.log(`Test complete. Email used: ${data.email}`);
}
