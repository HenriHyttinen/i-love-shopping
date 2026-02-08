(function () {
  const GUEST_KEY = "guest_cart_token";

  let accessToken = "";

  function setAccessToken(token) {
    accessToken = token || "";
  }

  function getAccessToken() {
    return accessToken;
  }

  function getGuestToken() {
    return localStorage.getItem(GUEST_KEY) || "";
  }

  function setGuestToken(token) {
    if (token) {
      localStorage.setItem(GUEST_KEY, token);
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
    const fetchOpts = {
      method: options.method || "GET",
      headers: headers({ auth: options.auth, guest: options.guest, json: options.json }),
    };
    if (options.body !== undefined) {
      fetchOpts.body = options.json === false ? options.body : JSON.stringify(options.body);
    }

    let res;
    try {
      res = await fetch(url, fetchOpts);
    } catch (_) {
      throw { detail: "Network error. Please retry." };
    }

    const data = await res.json().catch(() => ({}));
    if (data && data.guest_cart_token) setGuestToken(data.guest_cart_token);

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

  function fmtMoney(value) {
    const n = Number(value || 0);
    return "$" + n.toFixed(2);
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
    API: "http://localhost:8000/api",
    setAccessToken,
    getAccessToken,
    getGuestToken,
    setGuestToken,
    request,
    byId,
    setStatus,
    fmtMoney,
    esc,
  };
})();
