import http from "k6/http";
import { check } from "k6";

// ---------------------------------------------------------------------------
// Smoke test: 1 VU, quick sanity check that endpoints respond before
// running the full 50-VU load test.
// ---------------------------------------------------------------------------
const BASE_URL = __ENV.BASE_URL || "http://localhost:5000";

export const options = {
  vus: 1,
  iterations: 1,
};

export default function () {
  const endpoints = [
    { method: "GET", url: `${BASE_URL}/health` },
    { method: "GET", url: `${BASE_URL}/users` },
    { method: "GET", url: `${BASE_URL}/urls` },
    { method: "GET", url: `${BASE_URL}/events` },
  ];

  for (const ep of endpoints) {
    const res = http.get(ep.url);
    check(res, {
      [`${ep.method} ${ep.url} is reachable`]: (r) => r.status < 500,
    });
    console.log(`${ep.method} ${ep.url} => ${res.status} (${res.timings.duration}ms)`);
  }
}
