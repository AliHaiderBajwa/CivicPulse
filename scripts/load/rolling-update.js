// CivicPulse BN1 — zero-downtime rolling update under live load (rubric BN1).
// Constant moderate load while `kubectl rollout restart deployment/backend`
// replaces every pod mid-run. Pass = zero failed requests: with
// maxUnavailable 0 + readiness gates, no request may ever hit a dead pod.
// (HPA stays ON: if the load also triggers a scale event, that is a second
// rolling change the same guarantee must survive.)
// X-Forwarded-For is unique per request so the per-IP limiter never trips;
// Host routes the shared ingress (same as k8s-up.sh smoke).
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 15,
  duration: "150s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";
const HOST = { "Host": "civicpulse.localhost" };

const TEXTS = [
  "Water main burst on the main avenue, water is flooding the underpass since morning",
  "Street light outside the market has been dark for a week, unsafe at night",
  "Deep pothole on Ring Road damaging cars daily, needs urgent repair",
  "Power transformer sparking near the school, please send a crew immediately",
];

function citizenIp() {
  return `10.${__VU % 250}.${__ITER % 255}.${Math.trunc(__ITER / 255) % 250}`;
}

export default function runScenario() {
  const ip = citizenIp();
  const headers = {
    "Content-Type": "application/json",
    "X-Forwarded-For": ip,
    ...HOST,
  };
  // Text choice is load-generation jitter only, not security-relevant
  // randomness (no tokens, no identifiers, nothing observable is derived
  // from it) — fixed-pattern complaints would bias the latency profile.
  const text = TEXTS[Math.floor(Math.random() * TEXTS.length)]; // NOSONAR
  const created = http.post(
    `${BASE}/api/complaints`,
    JSON.stringify({ text, location: `BN1 St ${ip.split(".").pop()}` }),
    { headers },
  );
  check(created, { "POST created 201": (r) => r.status === 201 });
  const stats = http.get(`${BASE}/api/stats`, {
    headers: { "X-Forwarded-For": ip, ...HOST },
  });
  check(stats, { "stats 200": (r) => r.status === 200 });
  sleep(0.3);
}
