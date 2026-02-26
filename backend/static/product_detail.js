(function () {
  const U = window.ShopUI;

  function productIdFromPath() {
    const m = location.pathname.match(/^\/products\/(\d+)\/?$/);
    return m ? Number(m[1]) : 0;
  }

  function ratingMarkup(value) {
    const numeric = Math.max(0, Math.min(5, Number(value || 0)));
    const rounded = Math.round(numeric);
    const stars = "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
    return `<span class="muted" aria-label="Average rating ${numeric.toFixed(1)} out of 5">${stars} ${numeric.toFixed(1)}/5</span>`;
  }

  function imageUrl(item) {
    if (!item || !item.image) return "";
    if (item.image.startsWith("http") || item.image.startsWith("/")) return item.image;
    return "/media/" + item.image;
  }

  let currentProduct = null;

  function renderProduct(product) {
    currentProduct = product;
    const first = Array.isArray(product.images) && product.images.length ? product.images[0] : null;
    const img = imageUrl(first);
    U.byId("pdp-main").innerHTML = `
      <div class="cols-2">
        <div>
          ${img ? `<img src="${U.esc(img)}" alt="${U.esc(product.name)}" style="width:100%;max-height:360px;object-fit:cover;border-radius:12px;border:1px solid var(--line);">` : ""}
        </div>
        <div>
          <h1 style="margin-bottom:6px;">${U.esc(product.name)}</h1>
          <div class="muted">${U.esc(product.brand.name)} • ${U.esc(product.category.name)}</div>
          <div style="margin:8px 0;">${ratingMarkup(product.rating)}</div>
          <p class="muted" style="margin:8px 0 12px;">${U.esc(product.description)}</p>
          <div class="badge">Stock ${product.stock_quantity}</div>
          <div style="font-weight:800;font-size:20px;margin:12px 0;">${U.fmtMoney(product.price)}</div>
          <div class="btn-row">
            <input id="pdp-qty" type="number" min="1" value="1" style="max-width:120px;">
            <button id="pdp-add-btn">Add to Cart</button>
          </div>
        </div>
      </div>
    `;

    U.byId("pdp-add-btn").addEventListener("click", async () => {
      try {
        const qty = Math.max(1, Number(U.byId("pdp-qty").value || 1));
        await U.request(U.API + "/commerce/cart/items/", {
          method: "POST",
          auth: true,
          body: { product_id: product.id, quantity: qty },
        });
        U.setStatus("pdp-status", "Added to cart.", "ok");
      } catch (err) {
        U.setStatus("pdp-status", U.errorText(err), "error");
      }
    });
  }

  function reviewCard(review) {
    return `
      <article class="product">
        <div style="display:flex;justify-content:space-between;gap:10px;">
          <strong>${U.esc(review.user_name || "Customer")}</strong>
          ${ratingMarkup(review.rating)}
        </div>
        <p class="muted" style="margin:8px 0;">${U.esc(review.comment)}</p>
        <div class="btn-row" style="align-items:center;">
          <span class="badge">${review.helpful_votes || 0} helpful</span>
          <button class="secondary" data-helpful="${review.id}" style="min-width:160px;">
            ${review.voted_helpful ? "Remove Helpful Vote" : "Mark as Helpful"}
          </button>
        </div>
      </article>
    `;
  }

  async function loadReviews(productId) {
    const data = await U.request(U.API + "/catalog/products/" + productId + "/reviews/", { auth: true });
    const root = U.byId("review-list");
    if (!data.length) {
      root.innerHTML = "<div class='muted'>No reviews yet. Be the first to review.</div>";
      return;
    }
    root.innerHTML = data.map(reviewCard).join("");
    root.querySelectorAll("button[data-helpful]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const reviewId = Number(btn.getAttribute("data-helpful"));
        try {
          await U.request(U.API + "/catalog/reviews/" + reviewId + "/helpful/", {
            method: "POST",
            auth: true,
            body: {},
          });
          await loadReviews(productId);
          U.setStatus("pdp-status", "Review feedback updated.", "ok");
        } catch (err) {
          U.setStatus("pdp-status", U.errorText(err), "error");
        }
      });
    });
  }

  async function loadRelated(product) {
    const root = U.byId("related-products");
    try {
      const data = await U.request(
        U.API + "/catalog/products/?category=" + encodeURIComponent(product.category.slug) + "&ordering=-rating",
        { guest: false }
      );
      const filtered = (data || []).filter((p) => p.id !== product.id).slice(0, 4);
      if (!filtered.length) {
        root.innerHTML = "<div class='muted'>No related products found.</div>";
        return;
      }
      root.innerHTML = filtered
        .map(
          (p) => `
            <article class="product">
              <h3>${U.esc(p.name)}</h3>
              <div class="muted">${U.esc(p.brand.name)} • ${U.esc(p.category.name)}</div>
              <div style="margin:8px 0;">${ratingMarkup(p.rating)}</div>
              <div style="font-weight:700;margin-bottom:8px;">${U.fmtMoney(p.price)}</div>
              <a class="btn-link" href="/products/${p.id}/">View Details</a>
            </article>
          `
        )
        .join("");
    } catch (_) {
      root.innerHTML = "<div class='muted'>Could not load related products.</div>";
    }
  }

  async function submitReview(productId) {
    try {
      const payload = {
        rating: Number(U.byId("review-rating").value || 5),
        comment: U.byId("review-comment").value.trim(),
      };
      await U.request(U.API + "/catalog/products/" + productId + "/reviews/", {
        method: "POST",
        auth: true,
        body: payload,
      });
      U.byId("review-comment").value = "";
      await loadReviews(productId);
      const refreshed = await U.request(U.API + "/catalog/products/" + productId + "/", { guest: false });
      renderProduct(refreshed);
      U.setStatus("pdp-status", "Review submitted.", "ok");
    } catch (err) {
      U.setStatus("pdp-status", U.errorText(err), "error");
    }
  }

  async function init() {
    const productId = productIdFromPath();
    if (!productId) {
      U.setStatus("pdp-status", "Invalid product page.", "error");
      return;
    }
    try {
      const product = await U.request(U.API + "/catalog/products/" + productId + "/", { guest: false });
      renderProduct(product);
      await loadReviews(productId);
      await loadRelated(product);
      U.setStatus("pdp-status", "Product loaded.", "info");
    } catch (err) {
      U.setStatus("pdp-status", U.errorText(err), "error");
    }

    U.byId("review-submit-btn").addEventListener("click", () => submitReview(productId));
  }

  init();
})();
