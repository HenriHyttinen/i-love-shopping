import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 20,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(90)<2000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const guestToken = `load-${__VU}-${Date.now()}`;
  const headers = {
    "Content-Type": "application/json",
    "X-Guest-Cart-Token": guestToken,
  };

  const add = http.post(
    `${BASE_URL}/api/commerce/cart/items/`,
    JSON.stringify({ product_id: 1, quantity: 1 }),
    { headers },
  );
  check(add, { "add to cart status": (r) => r.status === 201 || r.status === 200 });

  const checkout = http.post(
    `${BASE_URL}/api/commerce/checkout/place-order/`,
    JSON.stringify({
      full_name: "Load Test User",
      email: `load+${__VU}@example.com`,
      phone: "+358401234567",
      shipping_address: {
        line1: "Main Street 1",
        city: "Helsinki",
        state: "Uusimaa",
        postal_code: "00100",
        country: "FI",
      },
      shipping_option: "standard",
      payment_method: "stripe_sandbox",
      payment_token: "tok_success",
    }),
    { headers },
  );
  check(checkout, {
    "checkout responded": (r) => r.status === 201 || r.status === 400 || r.status === 409,
  });
  sleep(1);
}
