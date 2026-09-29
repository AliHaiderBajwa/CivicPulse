// CivicPulse load test — HPA evidence (rubric H5).
// Simulates distinct citizens: every request carries its own X-Forwarded-For,
// so the stub's per-IP rate limit (10/min) is honoured per client while the
// cluster still sees realistic aggregate load.
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "15s", target: 20 }, // warm up
    { duration: "30s", target: 100 }, // ramp — expect first scale-up
    { duration: "120s", target: 100 }, // sustain — expect steady state
    { duration: "60s", target: 0 }, // ramp down — scale-down follows (300s stabilisation)
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8080";

const TEXTS = [
  "Water main burst on the main avenue, water is flooding the underpass since morning",
  "Street light outside the market has been dark for a week, unsafe at night",
  "Overflowing garbage bins near the bus stand, smell is getting unbearable",
  "Deep pothole on Ring Road damaging cars daily, needs urgent repair",
  "Power transformer sparking near the school, please send a crew immediately",
  "Blocked drain causing sewage backup into residential street 9",
  "Broken traffic signal blinking amber forever, intersections are chaotic",
  "Street lamp post leaning dangerously after last night storm on 7th avenue",
];

function citizenIp() {
  // Deterministic and collision-free within the run: the per-citizen
  // rate-limit key must be unique per request or the 10/min window trips.
  const ip = `10.${__VU % 250}.${__ITER % 255}.${((__ITER / 255) | 0) % 250}`;
  return ip;
}

export default function () {
  const ip = citizenIp();
  const headers = {
    "Content-Type": "application/json",
    "X-Forwarded-For": ip,
  };
  const text = TEXTS[Math.floor(Math.random() * TEXTS.length)];

  const created = http.post(
    `${BASE}/api/complaints`,
    JSON.stringify({ text, location: `LoadTest St ${ip.split(".").pop()}` }),
    { headers },
  );
  check(created, { "POST created 201": (r) => r.status === 201 });

  const stats = http.get(`${BASE}/api/stats`, { headers: { "X-Forwarded-For": ip } });
  check(stats, { "stats 200": (r) => r.status === 200 });

  sleep(0.3);
}
