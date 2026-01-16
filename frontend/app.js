let accessToken = "";
let recaptchaSiteKey = "";
let recaptchaWidgetId = null;

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function isStrongEnoughPassword(value) {
  return value.length >= 8;
}

function isValidTwoFACode(value) {
  return /^[0-9]{6,8}$/.test(value);
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function setAuthStatus(text) {
  document.getElementById("auth-status").textContent = text;
}

async function handleGoogleRedirectCode() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  if (!code) return;
  try {
    setText("google-result", "Completing Google login...");
    const payload = await postJson("http://localhost:8000/api/auth/oauth/google-code/", {
      code,
      redirect_uri: window.location.origin,
    });
    accessToken = payload.access;
    setAuthStatus("Logged in (JWT)");
    setText("google-result", "Google login OK.");
  } catch (err) {
    setText("google-result", JSON.stringify(err));
  } finally {
    params.delete("code");
    params.delete("scope");
    params.delete("authuser");
    params.delete("prompt");
    const newUrl = `${window.location.pathname}${params.toString() ? `?${params}` : ""}`;
    window.history.replaceState({}, document.title, newUrl);
  }
}

function setLoginTwoFAVisible(visible) {
  const container = document.getElementById("login-2fa");
  if (!container) return;
  container.classList.toggle("hidden", !visible);
}

function isTwoFARequiredError(err) {
  if (!err) return false;
  const message = typeof err === "string" ? err : JSON.stringify(err);
  return message.includes("Two-factor code required");
}

function tryRenderRecaptcha() {
  if (!recaptchaSiteKey || !window.grecaptcha || recaptchaWidgetId !== null) {
    return;
  }
  recaptchaWidgetId = grecaptcha.render("recaptcha-container", {
    sitekey: recaptchaSiteKey,
  });
}

async function loadGoogleClientId() {
  try {
    const data = await getJson("http://localhost:8000/api/auth/oauth/google-client-id/");
    if (data.client_id) {
      document.getElementById("google-client-id").value = data.client_id;
      setText("google-result", "Client ID loaded.");
    }
  } catch (_) {
    setText("google-result", "Could not load Client ID.");
  }
}

async function loadRecaptchaSiteKey() {
  try {
    const data = await getJson("http://localhost:8000/api/auth/recaptcha-site-key/");
    if (data.site_key) {
      recaptchaSiteKey = data.site_key;
      tryRenderRecaptcha();
    }
  } catch (_) {
    setText("reg-result", "Could not load reCAPTCHA site key.");
  }
}

async function postJson(url, data, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw payload;
  return payload;
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw payload;
  }
  return res.json();
}

function buildSearchParams() {
  const params = new URLSearchParams();
  const q = document.getElementById("search-q").value;
  const min = document.getElementById("search-min").value;
  const max = document.getElementById("search-max").value;
  const brand = document.getElementById("search-brand").value;
  const category = document.getElementById("search-category").value;
  const ordering = document.getElementById("search-order").value;

  if (q) params.append("search", q);
  if (min) params.append("min_price", min);
  if (max) params.append("max_price", max);
  if (brand) params.append("brand", brand);
  if (category) params.append("category", category);
  if (ordering) params.append("ordering", ordering);

  return params.toString();
}

function renderProducts(products) {
  const grid = document.getElementById("product-grid");
  grid.innerHTML = "";
  if (!products.length) {
    grid.innerHTML = "<div class=\"muted\">No products found.</div>";
    return;
  }
  const origin = window.location.origin;
  products.forEach((product) => {
    const card = document.createElement("div");
    card.className = "product-card";
    const images = Array.isArray(product.images) ? product.images : [];
    const preferred =
      images.find((img) => img.image && !img.image.includes("_sample")) || images[0];
    const rawUrl = preferred ? preferred.image : "";
    const imageUrl = rawUrl
      ? rawUrl.startsWith("http") || rawUrl.startsWith("/")
        ? rawUrl
        : `${origin}/media/${rawUrl}`
      : "";
    card.innerHTML = `
      <h3>${product.name}</h3>
      ${imageUrl ? `<img src="${imageUrl}" alt="${(preferred && preferred.alt_text) || product.name}" class="product-image">` : ""}
      <div class="product-meta">${product.brand.name} • ${product.category.name}</div>
      <div class="product-meta">Stock: ${product.stock_quantity}</div>
      <div class="price-tag">$${product.price}</div>
    `;
    grid.appendChild(card);
  });
}

let suggestTimer = null;

async function runSuggest(query) {
  const q = (query ?? document.getElementById("search-q").value).trim();
  if (!q) {
    document.getElementById("search-output").textContent = "[]";
    setText("search-result", "0 suggestions");
    return;
  }
  try {
    const data = await getJson(
      `http://localhost:8000/api/catalog/suggest/?q=${encodeURIComponent(q)}`
    );
    document.getElementById("search-output").textContent = JSON.stringify(data, null, 2);
    renderProducts([]);
    setText("search-result", `${data.length} suggestions`);
  } catch (err) {
    renderProducts([]);
    setText("search-result", JSON.stringify(err));
  }
}

async function runSearch() {
  const qs = buildSearchParams();
  try {
    const data = await getJson(`http://localhost:8000/api/catalog/products/?${qs}`);
    document.getElementById("search-output").textContent = JSON.stringify(data, null, 2);
    renderProducts(data);
    setText("search-result", `${data.length} products`);
  } catch (err) {
    renderProducts([]);
    setText("search-result", JSON.stringify(err));
  }
}

document.getElementById("reg-btn").addEventListener("click", async () => {
  try {
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const fullName = document.getElementById("reg-name").value.trim();
    if (!email || !password || !fullName) {
      setText("reg-result", "Email, password, and full name are required.");
      return;
    }
    if (!isValidEmail(email)) {
      setText("reg-result", "Enter a valid email.");
      return;
    }
    if (!isStrongEnoughPassword(password)) {
      setText("reg-result", "Password must be at least 8 characters.");
      return;
    }
    if (recaptchaWidgetId === null) {
      setText("reg-result", "reCAPTCHA not loaded.");
      return;
    }
    const recaptchaToken = grecaptcha.getResponse(recaptchaWidgetId);
    if (!recaptchaToken) {
      setText("reg-result", "Please complete the reCAPTCHA.");
      return;
    }
    await postJson("http://localhost:8000/api/auth/register/", {
      email,
      password,
      full_name: fullName,
      recaptcha_token: recaptchaToken,
    });
    grecaptcha.reset(recaptchaWidgetId);
    setText("reg-result", "Registered. Now login.");
  } catch (err) {
    setText("reg-result", JSON.stringify(err));
  }
});

document.getElementById("login-btn").addEventListener("click", async () => {
  try {
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    const code = document.getElementById("login-code").value.trim();
    if (!email || !password) {
      setText("login-result", "Email and password are required.");
      return;
    }
    if (!isValidEmail(email)) {
      setText("login-result", "Enter a valid email.");
      return;
    }
    if (code && !isValidTwoFACode(code)) {
      setText("login-result", "2FA code must be 6-8 digits.");
      return;
    }
    const loginPayload = { email, password };
    if (code) {
      loginPayload.code = code;
    }
    const payload = await postJson("http://localhost:8000/api/auth/login/", loginPayload);
    accessToken = payload.access;
    setAuthStatus("Logged in");
    setText("login-result", "Login ok. Access token stored in memory.");
    if (!code) {
      setLoginTwoFAVisible(false);
    }
  } catch (err) {
    if (isTwoFARequiredError(err)) {
      setLoginTwoFAVisible(true);
      setText("login-result", "2FA enabled. Enter your code to continue.");
      return;
    }
    setText("login-result", JSON.stringify(err));
  }
});

document.getElementById("google-login-btn").addEventListener("click", async () => {
  const clientId = document.getElementById("google-client-id").value.trim();
  if (!clientId) {
    setText("google-result", "Client ID required.");
    return;
  }
  if (!window.google || !google.accounts || !google.accounts.oauth2) {
    setText("google-result", "Google script not loaded yet.");
    return;
  }
  const codeClient = google.accounts.oauth2.initCodeClient({
    client_id: clientId,
    scope: "openid email profile",
    ux_mode: "redirect",
    redirect_uri: window.location.origin,
  });
  codeClient.requestCode();
});

handleGoogleRedirectCode();
loadGoogleClientId();
loadRecaptchaSiteKey();

window.onRecaptchaLoaded = function () {
  tryRenderRecaptcha();
};

document.getElementById("logout-all-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("login-result", "Login first.");
    return;
  }
  try {
    await postJson("http://localhost:8000/api/auth/logout-all/", {}, accessToken);
    setAuthStatus("Logged out");
    setText("login-result", "Logged out all sessions.");
  } catch (err) {
    setText("login-result", JSON.stringify(err));
  }
});

document.getElementById("revoke-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("login-result", "Login first.");
    return;
  }
  try {
    await postJson("http://localhost:8000/api/auth/token/revoke/", {}, accessToken);
    setAuthStatus("Logged out");
    setText("login-result", "Access token revoked.");
  } catch (err) {
    setText("login-result", JSON.stringify(err));
  }
});

document.getElementById("twofa-setup-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("twofa-setup-result", "Login first.");
    return;
  }
  try {
    const payload = await postJson("http://localhost:8000/api/auth/2fa/setup/", {}, accessToken);
    setText("twofa-setup-result", "Scan QR and verify code.");
    const img = document.getElementById("twofa-qr");
    img.src = `data:image/png;base64,${payload.qr_code_base64}`;
    img.style.display = "block";
  } catch (err) {
    setText("twofa-setup-result", JSON.stringify(err));
  }
});

document.getElementById("twofa-verify-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("twofa-verify-result", "Login first.");
    return;
  }
  try {
    const code = document.getElementById("twofa-code").value.trim();
    if (!isValidTwoFACode(code)) {
      setText("twofa-verify-result", "Enter a valid 6-8 digit code.");
      return;
    }
    await postJson(
      "http://localhost:8000/api/auth/2fa/verify/",
      { code },
      accessToken
    );
    setText("twofa-verify-result", "2FA enabled.");
    setLoginTwoFAVisible(true);
  } catch (err) {
    setText("twofa-verify-result", JSON.stringify(err));
  }
});

document.getElementById("twofa-disable-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("twofa-verify-result", "Login first.");
    return;
  }
  try {
    const code = document.getElementById("twofa-code").value.trim();
    if (!isValidTwoFACode(code)) {
      setText("twofa-verify-result", "Enter a valid 6-8 digit code.");
      return;
    }
    await postJson(
      "http://localhost:8000/api/auth/2fa/disable/",
      { code },
      accessToken
    );
    setText("twofa-verify-result", "2FA disabled.");
    setLoginTwoFAVisible(false);
  } catch (err) {
    setText("twofa-verify-result", JSON.stringify(err));
  }
});

document.getElementById("reset-btn").addEventListener("click", async () => {
  try {
    const email = document.getElementById("reset-email").value.trim();
    if (!email) {
      setText("reset-result", "Email is required.");
      return;
    }
    if (!isValidEmail(email)) {
      setText("reset-result", "Enter a valid email.");
      return;
    }
    await postJson("http://localhost:8000/api/auth/password/reset/", {
      email,
    });
    setText("reset-result", "Reset email sent (check console/email backend)." );
  } catch (err) {
    setText("reset-result", JSON.stringify(err));
  }
});

document.getElementById("search-btn").addEventListener("click", async () => {
  runSearch();
});

document.getElementById("search-q").addEventListener("input", (event) => {
  const value = event.target.value;
  if (suggestTimer) {
    clearTimeout(suggestTimer);
  }
  suggestTimer = setTimeout(() => {
    runSuggest(value);
  }, 300);
});

document.getElementById("suggest-btn").addEventListener("click", async () => {
  runSuggest();
});

document.getElementById("img-upload-btn").addEventListener("click", async () => {
  if (!accessToken) {
    setText("img-upload-result", "Login as admin first.");
    return;
  }
  const productId = document.getElementById("img-product-id").value;
  const altText = document.getElementById("img-alt").value;
  const fileInput = document.getElementById("img-file");
  if (!productId || !fileInput.files.length) {
    setText("img-upload-result", "Product ID and image required.");
    return;
  }
  const formData = new FormData();
  formData.append("image", fileInput.files[0]);
  formData.append("alt_text", altText);
  try {
    const res = await fetch(`http://localhost:8000/api/catalog/products/${productId}/images/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw payload;
    setText("img-upload-result", "Image uploaded.");
  } catch (err) {
    setText("img-upload-result", JSON.stringify(err));
  }
});

runSearch();
