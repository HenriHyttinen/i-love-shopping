import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 50,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(90)<2000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const res = http.get(`${BASE_URL}/api/catalog/products/?ordering=rating`);
  check(res, {
    "status is 200": (r) => r.status === 200,
    "response has list": (r) => {
      try {
        const data = JSON.parse(r.body);
        return Array.isArray(data);
      } catch (_) {
        return false;
      }
    },
  });
  sleep(1);
}
