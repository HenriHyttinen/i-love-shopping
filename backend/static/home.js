(function () {
  const U = window.ShopUI;

  function buildSearchParams() {
    const params = new URLSearchParams();
    const q = U.byId("search-q").value.trim();
    const min = U.byId("search-min").value.trim();
    const max = U.byId("search-max").value.trim();
    const brand = U.byId("search-brand").value.trim();
    const category = U.byId("search-category").value.trim();
    const ordering = U.byId("search-order").value;

    if (q) params.append("search", q);
    if (min) params.append("min_price", min);
    if (max) params.append("max_price", max);
    if (brand) params.append("brand", brand);
    if (category) params.append("category", category);
    if (ordering) params.append("ordering", ordering);
    return params.toString();
  }

  async function loadCartBadge() {
    try {
      const data = await U.request(U.API + "/commerce/cart/");
      U.byId("cart-badge").textContent = data.item_count + " items";
    } catch (_) {
      U.byId("cart-badge").textContent = "0 items";
    }
  }

  function renderProducts(products) {
    const root = U.byId("products");
    if (!products.length) {
      root.innerHTML = '<div class="panel muted">No products found.</div>';
      return;
    }
    root.innerHTML = products
      .map((p) => {
        const firstImage = Array.isArray(p.images) && p.images.length ? p.images[0] : null;
        const img = firstImage ? firstImage.image : "";
        const imgUrl = img && !img.startsWith("http") && !img.startsWith("/") ? "/media/" + img : img;
        return `
          <article class="product">
            ${imgUrl ? `<img src="${U.esc(imgUrl)}" alt="${U.esc(p.name)}">` : ""}
            <h3>${U.esc(p.name)}</h3>
            <div class="muted">${U.esc(p.brand.name)} • ${U.esc(p.category.name)}</div>
            <div style="margin:8px 0"><span class="badge">Stock ${p.stock_quantity}</span></div>
            <div style="font-weight:700; margin-bottom:8px">${U.fmtMoney(p.price)}</div>
            <div class="btn-row">
              <button data-add="${p.id}">Add to Cart</button>
            </div>
          </article>
        `;
      })
      .join("");

    root.querySelectorAll("button[data-add]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const productId = Number(btn.getAttribute("data-add"));
          await U.request(U.API + "/commerce/cart/items/", {
            method: "POST",
            body: { product_id: productId, quantity: 1 },
          });
          U.setStatus("catalog-status", "Added to cart.", "ok");
          loadCartBadge();
        } catch (err) {
          U.setStatus("catalog-status", JSON.stringify(err), "error");
        }
      });
    });
  }

  async function runSearch() {
    try {
      const qs = buildSearchParams();
      const products = await U.request(U.API + "/catalog/products/?" + qs, { guest: false });
      renderProducts(products);
      U.byId("raw-products").textContent = JSON.stringify(products, null, 2);
      U.setStatus("catalog-status", products.length + " products loaded.", "info");
    } catch (err) {
      U.setStatus("catalog-status", JSON.stringify(err), "error");
    }
  }

  async function register() {
    try {
      const email = U.byId("reg-email").value.trim();
      const password = U.byId("reg-password").value;
      const fullName = U.byId("reg-name").value.trim();
      const recaptcha = U.byId("reg-captcha").value.trim();
      await U.request(U.API + "/auth/register/", {
        method: "POST",
        guest: false,
        body: {
          email: email,
          password: password,
          full_name: fullName,
          recaptcha_token: recaptcha || "ok",
        },
      });
      U.setStatus("auth-status", "Registered successfully.", "ok");
    } catch (err) {
      U.setStatus("auth-status", JSON.stringify(err), "error");
    }
  }

  async function login() {
    try {
      const email = U.byId("login-email").value.trim();
      const password = U.byId("login-password").value;
      const payload = await U.request(U.API + "/auth/login/", {
        method: "POST",
        guest: false,
        body: { email, password },
      });
      U.setAccessToken(payload.access);
      U.setStatus("auth-status", "Logged in. Access token is in memory only.", "ok");
    } catch (err) {
      U.setStatus("auth-status", JSON.stringify(err), "error");
    }
  }

  U.byId("search-btn").addEventListener("click", runSearch);
  U.byId("register-btn").addEventListener("click", register);
  U.byId("login-btn").addEventListener("click", login);

  runSearch();
  loadCartBadge();
})();
