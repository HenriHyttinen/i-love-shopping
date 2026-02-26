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

  window.ShopUI = {
    API: "/api",
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
