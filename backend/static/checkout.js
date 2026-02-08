(function () {
  const U = window.ShopUI;
  let stripe = null;
  let stripeCard = null;

  function payloadFromForm() {
    return {
      full_name: U.byId("full_name").value.trim(),
      email: U.byId("email").value.trim(),
      phone: U.byId("phone").value.trim(),
      shipping_address: {
        line1: U.byId("line1").value.trim(),
        city: U.byId("city").value.trim(),
        state: U.byId("state").value.trim(),
        postal_code: U.byId("postal_code").value.trim(),
        country: U.byId("country").value.trim(),
      },
      shipping_option: U.byId("shipping_option").value,
      payment_method: U.byId("payment_method").value,
      card_number: U.byId("card_number").value.trim(),
      expiry_month: Number(U.byId("expiry_month").value),
      expiry_year: Number(U.byId("expiry_year").value),
      cvv: U.byId("cvv").value.trim(),
    };
  }

  function validate(payload) {
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email);
    const phoneOk = /^[+0-9()\-\s]{7,20}$/.test(payload.phone);
    const postalOk = /^[A-Za-z0-9\-\s]{3,12}$/.test(payload.shipping_address.postal_code);
    if (!payload.full_name || !payload.email || !payload.phone) return "Missing required fields.";
    if (!payload.shipping_address.line1 || !payload.shipping_address.city || !payload.shipping_address.state || !payload.shipping_address.country) return "Missing required fields.";
    if (!emailOk) return "Invalid email format.";
    if (!phoneOk) return "Invalid phone format.";
    if (!postalOk) return "Invalid address format.";
    return "";
  }

  async function login() {
    try {
      const email = U.byId("auth-email").value.trim();
      const password = U.byId("auth-password").value;
      const data = await U.request(U.API + "/auth/login/", {
        method: "POST",
        guest: false,
        body: { email, password },
      });
      U.setAccessToken(data.access);
      U.setStatus("checkout-status", "Logged in. Use prefill now.", "ok");
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  async function prefill() {
    try {
      const data = await U.request(U.API + "/commerce/checkout/prefill/", { auth: true });
      U.byId("full_name").value = data.full_name || "";
      U.byId("email").value = data.email || "";
      U.setStatus("checkout-status", "Prefill loaded.", "info");
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  async function summary() {
    try {
      const data = await U.request(U.API + "/commerce/checkout/summary/", { auth: true });
      U.byId("checkout-json").textContent = JSON.stringify(data, null, 2);
      U.setStatus("checkout-status", "Order summary loaded.", "info");
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  async function initStripe() {
    try {
      const cfg = await U.request(U.API + "/commerce/checkout/payment-config/", { guest: false });
      if (!cfg.stripe_publishable_key || !window.Stripe) return;
      stripe = window.Stripe(cfg.stripe_publishable_key);
      const elements = stripe.elements();
      stripeCard = elements.create("card", { hidePostalCode: true });
      stripeCard.mount("#stripe-card");
      U.byId("stripe-wrap").style.display = "block";
    } catch (_) {
      // Optional feature.
    }
  }

  async function placeOrder() {
    try {
      const payload = payloadFromForm();
      const bad = validate(payload);
      if (bad) {
        U.setStatus("checkout-status", bad, "warn");
        return;
      }

      if (stripe && stripeCard && payload.payment_method === "stripe_sandbox") {
        const pm = await stripe.createPaymentMethod({
          type: "card",
          card: stripeCard,
          billing_details: { name: payload.full_name, email: payload.email },
        });
        if (pm.error) {
          U.setStatus("checkout-status", pm.error.message || "Payment validation failed.", "error");
          return;
        }
        delete payload.card_number;
        delete payload.expiry_month;
        delete payload.expiry_year;
        delete payload.cvv;
        payload.payment_token = pm.paymentMethod.id;
      }

      const data = await U.request(U.API + "/commerce/checkout/place-order/", {
        method: "POST",
        auth: true,
        body: payload,
      });
      U.byId("checkout-json").textContent = JSON.stringify(data, null, 2);
      U.byId("confirm").innerHTML = `
        <h3>Order Confirmation</h3>
        <div class="status ok">Order #${data.order.id} is ${data.order.status}. Payment ${data.payment.status}.</div>
        <p class="footer-note">Tracking: ${U.esc(data.order.tracking_code || "")}</p>
      `;
      U.setStatus("checkout-status", "Checkout completed.", "ok");
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  U.byId("auth-login-btn").addEventListener("click", login);
  U.byId("prefill-btn").addEventListener("click", prefill);
  U.byId("summary-btn").addEventListener("click", summary);
  U.byId("place-btn").addEventListener("click", placeOrder);

  summary();
  initStripe();
})();
