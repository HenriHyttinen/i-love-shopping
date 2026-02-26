(function () {
  const GUEST_KEY = "guest_cart_token";
  const ACCESS_KEY = "shop_access_token";

  // Keep auth state shared across pages/tabs. Migrate old session token once.
  const migratedSessionToken = sessionStorage.getItem(ACCESS_KEY) || "";
  let accessToken = localStorage.getItem(ACCESS_KEY) || migratedSessionToken;
  if (migratedSessionToken && !localStorage.getItem(ACCESS_KEY)) {
    localStorage.setItem(ACCESS_KEY, migratedSessionToken);
  }
  if (migratedSessionToken) {
    sessionStorage.removeItem(ACCESS_KEY);
  }

  function setAccessToken(token) {
    accessToken = token || "";
    if (accessToken) localStorage.setItem(ACCESS_KEY, accessToken);
    else localStorage.removeItem(ACCESS_KEY);
  }

  function getAccessToken() {
    return accessToken;
  }

  function getGuestToken() {
    return localStorage.getItem(GUEST_KEY) || "";
  }

  function setGuestToken(token) {
    if (token) localStorage.setItem(GUEST_KEY, token);
    else localStorage.removeItem(GUEST_KEY);
  }

  async function fetchCurrentUser() {
    if (!accessToken) return null;
    try {
      return await request("http://localhost:8000/api/auth/me/", { auth: true, guest: false });
    } catch (_) {
      return null;
    }
  }

  function headers(opts) {
    const options = opts || {};
    const h = {};
    if (options.json !== false) h["Content-Type"] = "application/json";
    if (options.auth && accessToken) h.Authorization = "Bearer " + accessToken;
    if (options.guest !== false) {
      const guest = getGuestToken();
      if (guest) h["X-Guest-Cart-Token"] = guest;
    }
    return h;
  }

  async function request(url, opts) {
    const options = opts || {};
    function buildFetchOptions(authEnabled) {
      const out = {
        method: options.method || "GET",
        headers: headers({ auth: authEnabled, guest: options.guest, json: options.json }),
      };
      if (options.body !== undefined) {
        out.body = options.json === false ? options.body : JSON.stringify(options.body);
      }
      return out;
    }

    function isInvalidTokenResponse(res, data) {
      if (!res || res.status !== 401) return false;
      const detail = String((data && data.detail) || "").toLowerCase();
      const code = String((data && data.code) || "").toLowerCase();
      return code === "token_not_valid" || detail.includes("token not valid") || detail.includes("given token not valid");
    }

    let res;
    let data = {};
    try {
      res = await fetch(url, buildFetchOptions(!!options.auth));
    } catch (_) {
      throw { detail: "Network error. Please retry." };
    }

    data = await res.json().catch(() => ({}));

    // Auto-recover from stale JWT in browser storage.
    if (options.auth && accessToken && isInvalidTokenResponse(res, data)) {
      setAccessToken("");
      try {
        res = await fetch(url, buildFetchOptions(false));
        data = await res.json().catch(() => ({}));
      } catch (_) {
        throw { detail: "Network error. Please retry." };
      }
    }

    if (data && Object.prototype.hasOwnProperty.call(data, "guest_cart_token")) {
      setGuestToken(data.guest_cart_token);
    }

    if (!res.ok) throw data;
    return data;
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(id, text, tone) {
    const el = byId(id);
    if (!el) return;
    el.className = "status " + (tone || "info");
    el.textContent = text;
  }

  function errorText(err) {
    if (!err) return "Unexpected error.";
    if (typeof err === "string") return err;
    if (err.detail) return String(err.detail);
    if (Array.isArray(err.non_field_errors) && err.non_field_errors.length) return String(err.non_field_errors[0]);
    if (typeof err === "object") {
      const firstKey = Object.keys(err)[0];
      const firstVal = err[firstKey];
      if (Array.isArray(firstVal) && firstVal.length) return `${firstKey}: ${firstVal[0]}`;
      if (typeof firstVal === "string") return `${firstKey}: ${firstVal}`;
    }
    return "Request failed. Please retry.";
  }

  async function withBusy(btn, busyLabel, work) {
    if (!btn) return work();
    if (btn.dataset.busy === "1") return;
    const originalLabel = btn.textContent;
    btn.dataset.busy = "1";
    btn.disabled = true;
    if (busyLabel) btn.textContent = busyLabel;
    try {
      return await work();
    } finally {
      btn.disabled = false;
      btn.dataset.busy = "0";
      btn.textContent = originalLabel;
    }
  }

  function fmtMoney(value) {
    const n = Number(value || 0);
    return n.toLocaleString("fi-FI", {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function esc(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function initGlobalQuickUX() {
    const root = document.createElement("div");
    root.className = "quick-ux";
    root.innerHTML = `
      <div class="quick-search-wrap">
        <input id="quick-search-input" type="text" placeholder="Quick search products..." />
        <div id="quick-search-suggestions" class="quick-suggestions" style="display:none;"></div>
      </div>
      <div class="quick-cart-wrap">
        <button id="quick-cart-btn" class="secondary">Cart Preview</button>
        <div id="quick-cart-popover" class="quick-cart-popover" style="display:none;">
          <div id="quick-cart-content" class="muted">Loading cart...</div>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    const searchInput = byId("quick-search-input");
    const suggestionBox = byId("quick-search-suggestions");
    const cartBtn = byId("quick-cart-btn");
    const cartPopover = byId("quick-cart-popover");
    const cartContent = byId("quick-cart-content");

    let suggestionTimer = null;
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim();
      if (suggestionTimer) clearTimeout(suggestionTimer);
      if (!query) {
        suggestionBox.style.display = "none";
        suggestionBox.innerHTML = "";
        return;
      }
      suggestionTimer = setTimeout(async () => {
        try {
          const data = await request(API + "/catalog/suggest/?q=" + encodeURIComponent(query), { guest: false });
          if (!Array.isArray(data) || !data.length) {
            suggestionBox.style.display = "none";
            suggestionBox.innerHTML = "";
            return;
          }
          suggestionBox.innerHTML = data
            .map((name) => `<a class="quick-suggestion-item" href="/search/?q=${encodeURIComponent(name)}">${esc(name)}</a>`)
            .join("");
          suggestionBox.style.display = "block";
        } catch (_) {
          suggestionBox.style.display = "none";
        }
      }, 250);
    });

    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) {
        suggestionBox.style.display = "none";
      }
    });

    cartBtn.addEventListener("click", async () => {
      const visible = cartPopover.style.display === "block";
      if (visible) {
        cartPopover.style.display = "none";
        return;
      }
      cartPopover.style.display = "block";
      cartContent.textContent = "Loading cart...";
      try {
        const cart = await request(API + "/commerce/cart/", { auth: true });
        if (!cart.items || !cart.items.length) {
          cartContent.innerHTML = "<div class='muted'>Cart is empty.</div>";
          return;
        }
        cartContent.innerHTML = `
          <div class="muted" style="margin-bottom:6px;">${cart.item_count} items • subtotal ${fmtMoney(cart.subtotal)}</div>
          <ul style="margin:0;padding-left:18px;">
            ${cart.items
              .slice(0, 5)
              .map((item) => `<li>${esc(item.name)} x ${item.quantity} • ${fmtMoney(item.line_total)}</li>`)
              .join("")}
          </ul>
          <div style="margin-top:8px;"><a class="btn-link" href="/cart/">Open full cart</a></div>
        `;
      } catch (err) {
        cartContent.textContent = errorText(err);
      }
    });
  }

  const API = "/api";

  function initCookieConsent() {
    const key = "cookie_consent";
    const current = localStorage.getItem(key);
    if (current === "accepted" || current === "declined") {
      return current === "accepted";
    }

    const banner = document.createElement("div");
    banner.className = "cookie-banner";
    banner.innerHTML = `
      <div>
        <strong>Cookie consent</strong>
        <div class="muted">We use cookies/local storage for cart persistence, login state, and security controls.</div>
      </div>
      <div class="btn-row">
        <button id="cookie-accept-btn">Accept</button>
        <button class="secondary" id="cookie-decline-btn">Decline</button>
      </div>
    `;
    document.body.appendChild(banner);

    const accept = () => {
      localStorage.setItem(key, "accepted");
      banner.remove();
    };
    const decline = () => {
      localStorage.setItem(key, "declined");
      setAccessToken("");
      setGuestToken("");
      banner.remove();
    };
    byId("cookie-accept-btn").addEventListener("click", accept);
    byId("cookie-decline-btn").addEventListener("click", decline);
    return false;
  }

  if (typeof window !== "undefined") {
    window.addEventListener("DOMContentLoaded", () => {
      const consentAccepted = initCookieConsent();
      if (consentAccepted) {
        initGlobalQuickUX();
      }
    });
  }

  window.ShopUI = {
    API,
    setAccessToken,
    getAccessToken,
    getGuestToken,
    setGuestToken,
    fetchCurrentUser,
    request,
    byId,
    setStatus,
    errorText,
    withBusy,
    fmtMoney,
    esc,
  };
})();
