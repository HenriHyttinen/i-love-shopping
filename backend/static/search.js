(function () {
  const U = window.ShopUI;
  const PAGE_SIZE = 8;
  let allResults = [];
  let currentPage = 1;

  function ratingMarkup(value) {
    const numeric = Math.max(0, Math.min(5, Number(value || 0)));
    const rounded = Math.round(numeric);
    const stars = "★".repeat(rounded) + "☆".repeat(Math.max(0, 5 - rounded));
    return `<div class="muted">${stars} ${numeric.toFixed(1)}/5</div>`;
  }

  function buildParams() {
    const params = new URLSearchParams();
    const fields = [
      ["search", "search-q"],
      ["brand", "search-brand"],
      ["category", "search-category"],
      ["min_price", "search-min"],
      ["max_price", "search-max"],
      ["ordering", "search-order"],
    ];
    fields.forEach(([param, id]) => {
      const value = U.byId(id).value.trim();
      if (value) params.append(param, value);
    });
    return params.toString();
  }

  function renderPage() {
    const total = allResults.length;
    const start = (currentPage - 1) * PAGE_SIZE;
    const slice = allResults.slice(start, start + PAGE_SIZE);
    U.byId("result-count").textContent = `${total} results`;
    U.byId("page-indicator").textContent = `Page ${currentPage}`;
    const root = U.byId("search-results");
    if (!slice.length) {
      root.innerHTML = "<div class='muted'>No results found.</div>";
      return;
    }
    root.innerHTML = slice
      .map(
        (p) => `
          <article class="product">
            <h3>${U.esc(p.name)}</h3>
            <div class="muted">${U.esc(p.brand.name)} • ${U.esc(p.category.name)}</div>
            ${ratingMarkup(p.rating)}
            <div style="font-weight:700;margin:8px 0;">${U.fmtMoney(p.price)}</div>
            <a class="btn-link" href="/products/${p.id}/">View Details</a>
          </article>
        `
      )
      .join("");
  }

  async function runSearch() {
    try {
      U.setStatus("search-status", "Searching...", "info");
      const data = await U.request(U.API + "/catalog/products/?" + buildParams(), { guest: false });
      allResults = data || [];
      currentPage = 1;
      renderPage();
      U.setStatus("search-status", "Results loaded.", "ok");
    } catch (err) {
      U.setStatus("search-status", U.errorText(err), "error");
    }
  }

  U.byId("search-btn").addEventListener("click", runSearch);
  U.byId("prev-page-btn").addEventListener("click", () => {
    if (currentPage > 1) {
      currentPage -= 1;
      renderPage();
    }
  });
  U.byId("next-page-btn").addEventListener("click", () => {
    if (currentPage * PAGE_SIZE < allResults.length) {
      currentPage += 1;
      renderPage();
    }
  });

  const initialQ = new URLSearchParams(location.search).get("q") || "";
  if (initialQ) U.byId("search-q").value = initialQ;
  runSearch();
})();
