(function () {
  const U = window.ShopUI;
  let stripe = null;
  let stripeCard = null;

  const SCENARIO_TOKEN_MAP = {
    success: "tok_success",
    insufficient_funds: "tok_fail_insufficient_funds",
    invalid_card_number: "tok_fail_invalid_card",
    expired_card: "tok_fail_expired_card",
    gateway_timeout: "tok_fail_gateway_timeout",
  };

  const CARD_FAILURE_TOKEN_MAP = {
    "4000000000009995": "tok_fail_insufficient_funds",
    "4000000000000002": "tok_fail_invalid_card",
    "4000000000000069": "tok_fail_expired_card",
    "4000000000000127": "tok_fail_gateway_timeout",
  };

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
      payment_token: U.byId("payment_token_manual").value.trim(),
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
    if (!payload.payment_method) return "Missing payment method.";
    return "";
  }

  function luhnValid(number) {
    let sum = 0;
    let alt = false;
    for (let i = number.length - 1; i >= 0; i -= 1) {
      let n = Number(number[i]);
      if (alt) {
        n *= 2;
        if (n > 9) n -= 9;
      }
      sum += n;
      alt = !alt;
    }
    return sum % 10 === 0;
  }

  function cardInput() {
    return {
      number: U.byId("card_number").value.trim().replace(/\s+/g, ""),
      month: Number(U.byId("expiry_month").value),
      year: Number(U.byId("expiry_year").value),
      cvv: U.byId("cvv").value.trim(),
    };
  }

  function validateCardInput(input) {
    if (!input.number && !input.month && !input.year && !input.cvv) return "";
    if (!/^\d{12,19}$/.test(input.number)) return "Invalid card number format.";
    if (!luhnValid(input.number)) return "Invalid card number checksum.";
    if (!Number.isInteger(input.month) || input.month < 1 || input.month > 12) return "Invalid expiry month.";
    if (!Number.isInteger(input.year) || input.year < 2000 || input.year > 2100) return "Invalid expiry year.";
    const now = new Date();
    const currentMonth = now.getUTCMonth() + 1;
    const currentYear = now.getUTCFullYear();
    if (input.year < currentYear || (input.year === currentYear && input.month < currentMonth)) return "Card has expired.";
    if (!/^\d{3,4}$/.test(input.cvv)) return "Invalid CVV format.";
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

  function useToken() {
    const token = U.byId("auth-token").value.trim();
    if (!token) {
      U.setStatus("checkout-status", "Paste an access token first.", "warn");
      return;
    }
    U.setAccessToken(token);
    U.setStatus("checkout-status", "Access token loaded.", "ok");
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
      renderSummary(data);
      U.setStatus("checkout-status", "Order summary loaded.", "info");
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  function renderSummary(data) {
    if (!data || !data.items) {
      U.byId("cart-summary").textContent = "Cart is empty.";
      return;
    }
    const rows = data.items
      .map((item) => `<li>${U.esc(item.name)} x ${item.quantity} • ${U.fmtMoney(item.line_total)}</li>`)
      .join("");
    U.byId("cart-summary").innerHTML = `
      <div><strong>${data.item_count}</strong> items, subtotal ${U.fmtMoney(data.subtotal)}</div>
      <ul style="margin:8px 0 0 18px">${rows}</ul>
    `;
  }

  async function initStripe() {
    try {
      const cfg = await U.request(U.API + "/commerce/checkout/payment-config/", { guest: false });
      if (!cfg.stripe_publishable_key || !window.Stripe) return;
      stripe = window.Stripe(cfg.stripe_publishable_key);
      const elements = stripe.elements();
      stripeCard = elements.create("card", { hidePostalCode: true });
      stripeCard.mount("#stripe-card");
      stripeCard.on("change", (event) => {
        if (event.error) {
          U.setStatus("checkout-status", event.error.message || "Payment validation failed.", "warn");
        }
      });
      updatePaymentUI();
    } catch (_) {
      // Optional feature.
    }
  }

  function scenarioToken() {
    const selected = U.byId("payment_scenario").value;
    return SCENARIO_TOKEN_MAP[selected] || SCENARIO_TOKEN_MAP.success;
  }

  function updatePaymentUI() {
    const method = U.byId("payment_method").value;
    const stripeVisible = method === "stripe_sandbox" && !!stripeCard;
    U.byId("stripe-wrap").style.display = stripeVisible ? "block" : "none";
  }

  async function placeOrder() {
    try {
      const payload = payloadFromForm();
      const bad = validate(payload);
      if (bad) {
        U.setStatus("checkout-status", bad, "warn");
        return;
      }

      if (payload.payment_method === "stripe_sandbox" && stripe && stripeCard) {
        const pm = await stripe.createPaymentMethod({
          type: "card",
          card: stripeCard,
          billing_details: { name: payload.full_name, email: payload.email },
        });
        if (pm.error) {
          U.setStatus("checkout-status", pm.error.message || "Payment validation failed.", "error");
          return;
        }
        payload.payment_token = pm.paymentMethod.id;
      } else if (!payload.payment_token) {
        const card = cardInput();
        const cardIssue = validateCardInput(card);
        if (cardIssue) {
          U.setStatus("checkout-status", cardIssue, "warn");
          return;
        }
        if (card.number) {
          payload.payment_token = CARD_FAILURE_TOKEN_MAP[card.number] || "tok_success";
        } else {
          payload.payment_token = scenarioToken();
        }
      }

      if (!payload.payment_token || payload.payment_token.length < 8) {
        U.setStatus("checkout-status", "Payment validation failed.", "error");
        return;
      }

      if (payload.payment_method === "paypal_sandbox" && !payload.payment_token.startsWith("tok_")) {
        U.setStatus("checkout-status", "PayPal sandbox requires a tok_* payment token.", "warn");
        return;
      }

      if (payload.payment_method === "stripe_sandbox" && !stripeCard && !payload.payment_token.startsWith("tok_")) {
        U.setStatus("checkout-status", "Stripe secure form unavailable. Use sandbox tok_* token or configure STRIPE_PUBLISHABLE_KEY.", "warn");
        return;
      }

      const data = await U.request(U.API + "/commerce/checkout/place-order/", {
        method: "POST",
        auth: true,
        body: payload,
      });
      const notification = data.notification || {};
      const notifyState = notification.status || "queued";
      const notifyRecipient = notification.recipient ? ` to ${U.esc(notification.recipient)}` : "";
      const notifyDetail = notification.detail ? U.esc(notification.detail) : "Notification status pending.";
      const notifyClass = notifyState === "sent" ? "ok" : (notifyState === "failed" ? "error" : "info");
      U.byId("checkout-json").textContent = JSON.stringify(data, null, 2);
      U.byId("confirm").innerHTML = `
        <h3>Order Confirmation</h3>
        <div class="status ok">Order #${data.order.id} is ${data.order.status}. Payment ${data.payment.status}.</div>
        <div class="status ${notifyClass}">Notification: ${U.esc(notifyState)}${notifyRecipient}. ${notifyDetail}</div>
        <p class="footer-note">Tracking: ${U.esc(data.order.tracking_code || "")}</p>
      `;
      if (notifyState === "failed") {
        U.setStatus("checkout-status", "Checkout completed, but email notification failed.", "warn");
      } else {
        U.setStatus("checkout-status", "Checkout completed.", "ok");
      }
    } catch (err) {
      U.setStatus("checkout-status", JSON.stringify(err), "error");
    }
  }

  U.byId("auth-login-btn").addEventListener("click", login);
  U.byId("auth-token-btn").addEventListener("click", useToken);
  U.byId("prefill-btn").addEventListener("click", prefill);
  U.byId("summary-btn").addEventListener("click", summary);
  U.byId("place-btn").addEventListener("click", placeOrder);
  U.byId("payment_method").addEventListener("change", updatePaymentUI);

  summary();
  updatePaymentUI();
  initStripe();
})();
