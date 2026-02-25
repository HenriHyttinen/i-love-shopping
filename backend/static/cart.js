(function () {
  const U = window.ShopUI;
  let cartRequestInFlight = false;
  const pendingQtyUpdates = new Map();
  const pendingQtyTimers = new Map();
  const AUTO_UPDATE_DELAY_MS = 350;

  function itemRow(item) {
    const thumb = item.thumbnail
      ? `<img src="${U.esc(item.thumbnail)}" alt="${U.esc(item.name)}" style="width:44px;height:44px;object-fit:cover;border-radius:8px;border:1px solid #1f2937;">`
      : `<div style="width:44px;height:44px;border-radius:8px;border:1px solid #1f2937;display:grid;place-items:center;color:#9ca3af;">N/A</div>`;
    return `
      <tr>
        <td><div class="btn-row" style="gap:8px;align-items:center;">${thumb}<span>Item #${item.id}</span></div></td>
        <td>${U.esc(item.name)}<div class="muted">Product #${item.product_id}</div></td>
        <td>${U.fmtMoney(item.price)}</td>
        <td>
          <div class="btn-row" style="gap:6px;">
            <button class="secondary" data-dec="${item.id}">-</button>
            <input data-qty-input="${item.id}" data-price="${item.price}" type="number" min="0" value="${item.quantity}" style="width:70px;">
            <button class="secondary" data-inc="${item.id}">+</button>
          </div>
        </td>
        <td data-line-total="${item.id}">${U.fmtMoney(item.line_total)}</td>
        <td>
          <div class="btn-row">
            <button class="secondary" data-edit="${item.id}">Update</button>
            <button class="danger" data-del="${item.id}">Remove</button>
          </div>
        </td>
      </tr>
    `;
  }

  function renderRecommended(items) {
    const root = U.byId("recommended");
    if (!items || !items.length) {
      root.innerHTML = "<div class='muted'>No recommendations yet.</div>";
      return;
    }
    root.innerHTML = items
      .map(
        (p) => `
          <article class="product">
            <h3>${U.esc(p.name)}</h3>
            <div class="muted">Stock ${p.stock_quantity}</div>
            <div style="font-weight:700; margin:8px 0">${U.fmtMoney(p.price)}</div>
            <div class="btn-row" style="gap:8px; align-items:center;">
              <input data-rec-qty="${p.id}" type="number" min="1" value="1" style="width:72px;">
              <button data-rec-add="${p.id}">Add</button>
            </div>
          </article>
        `
      )
      .join("");

    root.querySelectorAll("button[data-rec-add]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const productId = Number(btn.getAttribute("data-rec-add"));
        const qtyInput = root.querySelector(`input[data-rec-qty="${productId}"]`);
        const qty = Math.max(1, Number(qtyInput ? qtyInput.value : 1) || 1);
        addToCart(productId, qty);
      });
    });
  }

  function bindActions() {
    document.querySelectorAll("button[data-dec]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-dec"));
        const input = document.querySelector(`input[data-qty-input="${id}"]`);
        if (!input) return;
        const next = Math.max(0, Number(input.value || 0) - 1);
        input.value = next;
        refreshPendingTotals(id, next);
        queueAutoUpdate(id, next);
      });
    });

    document.querySelectorAll("button[data-inc]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-inc"));
        const input = document.querySelector(`input[data-qty-input="${id}"]`);
        if (!input) return;
        const next = Number(input.value || 0) + 1;
        input.value = next;
        refreshPendingTotals(id, next);
        queueAutoUpdate(id, next);
      });
    });

    document.querySelectorAll("input[data-qty-input]").forEach((input) => {
      input.addEventListener("input", () => {
        const id = Number(input.getAttribute("data-qty-input"));
        const qty = Number(input.value);
        if (Number.isNaN(qty) || qty < 0) return;
        refreshPendingTotals(id, qty);
        queueAutoUpdate(id, qty);
      });
    });

    document.querySelectorAll("button[data-edit]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-edit"));
        const input = document.querySelector(`input[data-qty-input="${id}"]`);
        const qty = input ? Number(input.value) : 0;
        if (Number.isNaN(qty) || qty < 0) return;
        clearQueuedUpdate(id);
        await updateItem(id, qty);
      });
    });

    document.querySelectorAll("button[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-del"));
        clearQueuedUpdate(id);
        await removeItem(id);
      });
    });
  }

  function renderCart(data) {
    U.byId("totals").textContent = `${data.item_count} items • subtotal ${U.fmtMoney(data.subtotal)}`;
    const tbody = U.byId("cart-rows");
    tbody.innerHTML = (data.items || []).map(itemRow).join("") || "<tr><td colspan='6' class='muted'>Cart is empty.</td></tr>";
    U.byId("cart-json").textContent = JSON.stringify(data, null, 2);
    renderRecommended(data.recommended_products || []);
    bindActions();
  }

  async function loadCart() {
    try {
      U.setStatus("cart-status", "Loading cart...", "info");
      const data = await U.request(U.API + "/commerce/cart/", { auth: true });
      renderCart(data);
      U.setStatus("cart-status", "Cart loaded.", "info");
    } catch (err) {
      U.setStatus("cart-status", U.errorText(err), "error");
    }
  }

  async function addToCart(productId, qty) {
    if (cartRequestInFlight) return;
    cartRequestInFlight = true;
    try {
      const data = await U.request(U.API + "/commerce/cart/items/", {
        method: "POST",
        auth: true,
        body: { product_id: productId, quantity: qty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Item added.", "ok");
    } catch (err) {
      U.setStatus("cart-status", U.errorText(err), "error");
    } finally {
      cartRequestInFlight = false;
    }
  }

  async function updateItem(itemId, qty) {
    if (cartRequestInFlight) return;
    cartRequestInFlight = true;
    try {
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "PATCH",
        auth: true,
        body: { quantity: qty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Item updated.", "ok");
    } catch (err) {
      U.setStatus("cart-status", U.errorText(err), "error");
    } finally {
      cartRequestInFlight = false;
      drainQueuedUpdates();
    }
  }

  function queueAutoUpdate(itemId, qty) {
    pendingQtyUpdates.set(itemId, qty);
    if (pendingQtyTimers.has(itemId)) {
      clearTimeout(pendingQtyTimers.get(itemId));
    }
    const timer = setTimeout(() => {
      pendingQtyTimers.delete(itemId);
      drainQueuedUpdates();
    }, AUTO_UPDATE_DELAY_MS);
    pendingQtyTimers.set(itemId, timer);
  }

  function clearQueuedUpdate(itemId) {
    pendingQtyUpdates.delete(itemId);
    if (pendingQtyTimers.has(itemId)) {
      clearTimeout(pendingQtyTimers.get(itemId));
      pendingQtyTimers.delete(itemId);
    }
  }

  function drainQueuedUpdates() {
    if (cartRequestInFlight || pendingQtyUpdates.size === 0) return;
    const [itemId, qty] = pendingQtyUpdates.entries().next().value;
    pendingQtyUpdates.delete(itemId);
    updateItem(itemId, qty);
  }

  function refreshPendingTotals(itemId, qty) {
    const lineCell = document.querySelector(`td[data-line-total="${itemId}"]`);
    const input = document.querySelector(`input[data-qty-input="${itemId}"]`);
    if (!lineCell || !input) return;
    const price = Number(input.getAttribute("data-price") || 0);
    const safeQty = Math.max(0, Number(qty) || 0);
    const lineTotal = price * safeQty;
    lineCell.textContent = U.fmtMoney(lineTotal);
    refreshPendingSubtotal();
  }

  function refreshPendingSubtotal() {
    let subtotal = 0;
    let itemCount = 0;
    document.querySelectorAll("input[data-qty-input]").forEach((input) => {
      const qty = Math.max(0, Number(input.value) || 0);
      const price = Number(input.getAttribute("data-price") || 0);
      subtotal += price * qty;
      if (qty > 0) itemCount += 1;
    });
    U.byId("totals").textContent = `${itemCount} items • subtotal ${U.fmtMoney(subtotal)}`;
  }

  async function removeItem(itemId) {
    if (cartRequestInFlight) return;
    cartRequestInFlight = true;
    try {
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "DELETE",
        auth: true,
      });
      renderCart(data);
      U.setStatus("cart-status", "Item removed.", "ok");
    } catch (err) {
      U.setStatus("cart-status", U.errorText(err), "error");
    } finally {
      cartRequestInFlight = false;
    }
  }

  U.byId("add-btn").addEventListener("click", () => {
    const productId = Number(U.byId("product-id").value);
    const qty = Number(U.byId("quantity").value || 1);
    addToCart(productId, qty);
  });

  U.byId("refresh-btn").addEventListener("click", loadCart);

  loadCart();
})();
