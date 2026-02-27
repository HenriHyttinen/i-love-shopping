(function () {
  const U = window.ShopUI;
  const pageSize = 8;
  let allProducts = [];
  let currentPage = 1;
  let currentView = "grid";

  function applyQueryPrefill() {
    const params = new URLSearchParams(window.location.search || "");
    const category = params.get("category") || "";
    const search = params.get("q") || "";
    if (category) U.byId("plp-category").value = category;
    if (search) U.byId("plp-search").value = search;
  }

  function ratingMarkup(value) {
    const numeric = Math.max(0, Math.min(5, Number(value || 0)));
    const rounded = Math.round(numeric);
    const stars = "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
    return `<div class="muted" aria-label="Average rating ${numeric.toFixed(1)} out of 5">${stars} ${numeric.toFixed(1)}/5</div>`;
  }

  function stockBadgeMarkup(stock) {
    const qty = Number(stock || 0);
    if (qty <= 0) return '<span class="badge" style="color:#ff9c9c;border-color:#7f3b43;">Out of Stock</span>';
    return `<span class="badge">In Stock: ${qty}</span>`;
  }

  function queryString() {
    const params = new URLSearchParams();
    const search = U.byId("plp-search").value.trim();
    const category = U.byId("plp-category").value.trim();
    const brand = U.byId("plp-brand").value.trim();
    const min = U.byId("plp-min").value.trim();
    const max = U.byId("plp-max").value.trim();
    const ordering = U.byId("plp-ordering").value;

    if (search) params.append("search", search);
    if (category) params.append("category", category);
    if (brand) params.append("brand", brand);
    if (min) params.append("min_price", min);
    if (max) params.append("max_price", max);
    if (ordering) params.append("ordering", ordering);
    return params.toString();
  }

  function pageCount() {
    return Math.max(1, Math.ceil(allProducts.length / pageSize));
  }

  function renderCurrentPage() {
    const root = U.byId("plp-products");
    const totalPages = pageCount();
    currentPage = Math.min(Math.max(currentPage, 1), totalPages);
    const start = (currentPage - 1) * pageSize;
    const items = allProducts.slice(start, start + pageSize);

    root.className = currentView === "grid" ? "product-grid" : "product-list";

    if (!items.length) {
      root.innerHTML = "<div class='muted'>No products found.</div>";
    } else {
      root.innerHTML = items
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
              <div style="margin:8px 0;">${stockBadgeMarkup(p.stock_quantity)}</div>
              <div style="font-weight:700; margin:8px 0">${U.fmtMoney(p.price)}</div>
              <a class="btn-link" href="/products/${p.id}/">View Product</a>
            </article>
          `;
        })
        .join("");
    }

    U.byId("plp-page-indicator").textContent = `Page ${currentPage} / ${totalPages}`;
    U.byId("plp-result-count").textContent = `${allProducts.length} results`;
    U.byId("plp-prev-btn").disabled = currentPage <= 1;
    U.byId("plp-next-btn").disabled = currentPage >= totalPages;
  }

  async function search() {
    try {
      U.setStatus("plp-status", "Loading products...", "info");
      const data = await U.request(U.API + "/catalog/products/?" + queryString(), { guest: false });
      allProducts = Array.isArray(data) ? data : [];
      currentPage = 1;
      renderCurrentPage();
      U.setStatus("plp-status", `${allProducts.length} products loaded.`, "ok");
    } catch (err) {
      U.setStatus("plp-status", U.errorText(err), "error");
    }
  }

  function toggleView() {
    const btn = U.byId("plp-toggle-view");
    currentView = currentView === "grid" ? "list" : "grid";
    btn.dataset.view = currentView;
    btn.textContent = currentView === "grid" ? "Switch to list view" : "Switch to grid view";
    renderCurrentPage();
  }

  U.byId("plp-search-btn").addEventListener("click", search);
  U.byId("plp-toggle-view").addEventListener("click", toggleView);
  U.byId("plp-prev-btn").addEventListener("click", () => {
    currentPage -= 1;
    renderCurrentPage();
  });
  U.byId("plp-next-btn").addEventListener("click", () => {
    currentPage += 1;
    renderCurrentPage();
  });

  applyQueryPrefill();
  search();
})();
