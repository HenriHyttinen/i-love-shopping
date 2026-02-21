(function () {
  const U = window.ShopUI;

  function ratingMarkup(value) {
    const numeric = Math.max(0, Math.min(5, Number(value || 0)));
    const rounded = Math.round(numeric);
    const stars = "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
    return `<div class="muted" aria-label="Average rating ${numeric.toFixed(1)} out of 5">${stars} ${numeric.toFixed(1)}/5</div>`;
  }

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
            ${ratingMarkup(p.rating)}
            <div style="margin:8px 0"><span class="badge">Stock ${p.stock_quantity}</span></div>
            <div style="font-weight:700; margin-bottom:8px">${U.fmtMoney(p.price)}</div>
            <div class="grid" style="grid-template-columns: 1fr 120px;">
              <input type="number" min="1" value="1" data-qty="${p.id}">
              <button data-add="${p.id}">Add</button>
            </div>
          </article>
        `;
      })
      .join("");

    root.querySelectorAll("button[data-add]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const productId = Number(btn.getAttribute("data-add"));
          const qtyInput = root.querySelector(`input[data-qty="${productId}"]`);
          const quantity = Math.max(1, Number(qtyInput ? qtyInput.value || 1 : 1));
          await U.request(U.API + "/commerce/cart/items/", {
            method: "POST",
            body: { product_id: productId, quantity },
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
      throw err;
    }
  }

  async function runSearchWithRetry(maxAttempts, delayMs) {
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        await runSearch();
        return;
      } catch (_) {
        // runSearch already sets UI status
      }
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  U.byId("search-btn").addEventListener("click", runSearch);

  runSearchWithRetry(3, 900);
  loadCartBadge();
})();
