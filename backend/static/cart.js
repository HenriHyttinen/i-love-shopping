(function () {
  const U = window.ShopUI;
  let cartRequestInFlight = false;

  function itemRow(item) {
    const thumb = item.thumbnail
      ? `<img src="${U.esc(item.thumbnail)}" alt="${U.esc(item.name)}" style="width:44px;height:44px;object-fit:cover;border-radius:8px;border:1px solid #1f2937;">`
      : `<div style="width:44px;height:44px;border-radius:8px;border:1px solid #1f2937;display:grid;place-items:center;color:#9ca3af;">N/A</div>`;
    return `
      <tr>
        <td><div class="btn-row" style="gap:8px;align-items:center;">${thumb}<span>#${item.id}</span></div></td>
        <td>${U.esc(item.name)}</td>
        <td>${U.fmtMoney(item.price)}</td>
        <td>
          <div class="btn-row" style="gap:6px;">
            <button class="secondary" data-dec="${item.id}">-</button>
            <input data-qty-input="${item.id}" type="number" min="0" value="${item.quantity}" style="width:70px;">
            <button class="secondary" data-inc="${item.id}">+</button>
          </div>
        </td>
        <td>${U.fmtMoney(item.line_total)}</td>
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
      });
    });

    document.querySelectorAll("button[data-inc]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-inc"));
        const input = document.querySelector(`input[data-qty-input="${id}"]`);
        if (!input) return;
        input.value = Number(input.value || 0) + 1;
      });
    });

    document.querySelectorAll("button[data-edit]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-edit"));
        const input = document.querySelector(`input[data-qty-input="${id}"]`);
        const qty = input ? Number(input.value) : 0;
        if (Number.isNaN(qty) || qty < 0) return;
        await updateItem(id, qty);
      });
    });

    document.querySelectorAll("button[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-del"));
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
      const data = await U.request(U.API + "/commerce/cart/");
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
        body: { quantity: qty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Item updated.", "ok");
    } catch (err) {
      U.setStatus("cart-status", U.errorText(err), "error");
    } finally {
      cartRequestInFlight = false;
    }
  }

  async function removeItem(itemId) {
    if (cartRequestInFlight) return;
    cartRequestInFlight = true;
    try {
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "DELETE",
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
