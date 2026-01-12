let accessToken = "";
let recaptchaSiteKey = "";
let recaptchaWidgetId = null;

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function setAuthStatus(text) {
  document.getElementById("auth-status").textContent = text;
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
  products.forEach((product) => {
    const card = document.createElement("div");
    card.className = "product-card";
    card.innerHTML = `
      <h3>${product.name}</h3>
      <div class="product-meta">${product.brand.name} • ${product.category.name}</div>
      <div class="product-meta">Stock: ${product.stock_quantity}</div>
      <div class="price-tag">$${product.price}</div>
    `;
    grid.appendChild(card);
  });
}

document.getElementById("reg-btn").addEventListener("click", async () => {
  try {
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
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-password").value,
      full_name: document.getElementById("reg-name").value,
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
    const payload = await postJson("http://localhost:8000/api/auth/login/", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
      code: document.getElementById("login-code").value,
    });
    accessToken = payload.access;
    setAuthStatus("Logged in");
    setText("login-result", "Login ok. Access token stored in memory.");
  } catch (err) {
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
  const tokenClient = google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: "openid email profile",
    callback: async (resp) => {
      try {
        const payload = await postJson("http://localhost:8000/api/auth/oauth/google/", {
          access_token: resp.access_token,
        });
        accessToken = payload.access;
        setAuthStatus("Logged in (JWT)");
        setText("google-result", "Google login OK.");
      } catch (err) {
        setText("google-result", JSON.stringify(err));
      }
    },
  });
  tokenClient.requestAccessToken();
});

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
    await postJson(
      "http://localhost:8000/api/auth/2fa/verify/",
      { code: document.getElementById("twofa-code").value },
      accessToken
    );
    setText("twofa-verify-result", "2FA enabled.");
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
    await postJson(
      "http://localhost:8000/api/auth/2fa/disable/",
      { code: document.getElementById("twofa-code").value },
      accessToken
    );
    setText("twofa-verify-result", "2FA disabled.");
  } catch (err) {
    setText("twofa-verify-result", JSON.stringify(err));
  }
});

document.getElementById("reset-btn").addEventListener("click", async () => {
  try {
    await postJson("http://localhost:8000/api/auth/password/reset/", {
      email: document.getElementById("reset-email").value,
    });
    setText("reset-result", "Reset email sent (check console/email backend).");
  } catch (err) {
    setText("reset-result", JSON.stringify(err));
  }
});

document.getElementById("search-btn").addEventListener("click", async () => {
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
});

document.getElementById("suggest-btn").addEventListener("click", async () => {
  const q = document.getElementById("search-q").value;
  try {
    const data = await getJson(`http://localhost:8000/api/catalog/suggest/?q=${encodeURIComponent(q)}`);
    document.getElementById("search-output").textContent = JSON.stringify(data, null, 2);
    renderProducts([]);
    setText("search-result", `${data.length} suggestions`);
  } catch (err) {
    renderProducts([]);
    setText("search-result", JSON.stringify(err));
  }
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
