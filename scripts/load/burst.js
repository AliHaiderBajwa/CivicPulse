// Short burst used only to capture `kubectl get hpa -w` output for evidence.
// The full load profile lives in loadtest.js.
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "10s", target: 80 },
    { duration: "60s", target: 80 },
    { duration: "10s", target: 0 },
  ],
  thresholds: { http_req_failed: ["rate<0.01"] },
};

const BASE = __ENV.BASE_URL || "http://civicpulse.localhost:8080";

export default function () {
  const headers = { "Content-Type": "application/json" };
  const res = http.post(
    `${BASE}/api/complaints`,
    JSON.stringify({
      text: "HPA watch burst request — capturing kubectl get hpa -w evidence for the report",
      location: `Watch St ${__VU}`,
    }),
    { headers },
  );
  check(res, { "created": (r) => r.status === 201 });
  sleep(0.4);
}
