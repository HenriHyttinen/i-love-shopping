import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 40,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(90)<2000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const ip = `10.11.${__VU}.${(__ITER % 250) + 1}`;
  const req = { headers: { "X-Forwarded-For": ip } };
  const search = http.get(`${BASE_URL}/api/catalog/products/?search=rtx&ordering=relevance`, req);
  check(search, { "search status 200": (r) => r.status === 200 });

  let productId = 1;
  try {
    const data = JSON.parse(search.body);
    if (Array.isArray(data) && data.length > 0) {
      productId = data[0].id || 1;
    }
  } catch (_) {
    productId = 1;
  }

  const pdp = http.get(`${BASE_URL}/api/catalog/products/${productId}/`, req);
  check(pdp, { "pdp status 200": (r) => r.status === 200 });
  sleep(1);
}
