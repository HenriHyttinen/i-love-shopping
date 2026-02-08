(function () {
  const U = window.ShopUI;

  function itemRow(item) {
    return `
      <tr>
        <td>#${item.id}</td>
        <td>${U.esc(item.name)}</td>
        <td>${U.fmtMoney(item.price)}</td>
        <td>${item.quantity}</td>
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
            <button data-rec-add="${p.id}">Add</button>
          </article>
        `
      )
      .join("");

    root.querySelectorAll("button[data-rec-add]").forEach((btn) => {
      btn.addEventListener("click", () => addToCart(Number(btn.getAttribute("data-rec-add")), 1));
    });
  }

  function bindActions() {
    document.querySelectorAll("button[data-edit]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.getAttribute("data-edit"));
        const qty = Number(prompt("New quantity (0 removes):", "1"));
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
      const data = await U.request(U.API + "/commerce/cart/");
      renderCart(data);
      U.setStatus("cart-status", "Cart loaded.", "info");
    } catch (err) {
      U.setStatus("cart-status", JSON.stringify(err), "error");
    }
  }

  async function addToCart(productId, qty) {
    try {
      const data = await U.request(U.API + "/commerce/cart/items/", {
        method: "POST",
        body: { product_id: productId, quantity: qty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Item added.", "ok");
    } catch (err) {
      U.setStatus("cart-status", JSON.stringify(err), "error");
    }
  }

  async function updateItem(itemId, qty) {
    try {
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "PATCH",
        body: { quantity: qty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Item updated.", "ok");
    } catch (err) {
      U.setStatus("cart-status", JSON.stringify(err), "error");
    }
  }

  async function removeItem(itemId) {
    try {
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "DELETE",
      });
      renderCart(data);
      U.setStatus("cart-status", "Item removed.", "ok");
    } catch (err) {
      U.setStatus("cart-status", JSON.stringify(err), "error");
    }
  }

  async function adjustQuantity(itemId, delta) {
    try {
      const cart = await U.request(U.API + "/commerce/cart/");
      const item = (cart.items || []).find((i) => i.id === itemId);
      if (!item) {
        U.setStatus("cart-status", "Item not found in cart.", "warn");
        return;
      }
      const nextQty = Math.max(0, Number(item.quantity) + Number(delta));
      const data = await U.request(U.API + "/commerce/cart/items/" + itemId + "/", {
        method: "PATCH",
        body: { quantity: nextQty },
      });
      renderCart(data);
      U.setStatus("cart-status", "Quantity updated.", "ok");
    } catch (err) {
      U.setStatus("cart-status", JSON.stringify(err), "error");
    }
  }

  U.byId("add-btn").addEventListener("click", () => {
    const productId = Number(U.byId("product-id").value);
    const qty = Number(U.byId("quantity").value || 1);
    addToCart(productId, qty);
  });

  U.byId("dec-btn").addEventListener("click", () => {
    const itemId = Number(U.byId("update-item-id").value);
    const dec = Number(U.byId("decrease-by").value || 1);
    if (!itemId) {
      U.setStatus("cart-status", "Provide item id.", "warn");
      return;
    }
    adjustQuantity(itemId, -dec);
  });

  U.byId("inc-btn").addEventListener("click", () => {
    const itemId = Number(U.byId("update-item-id").value);
    const inc = Number(U.byId("increase-by").value || 1);
    if (!itemId) {
      U.setStatus("cart-status", "Provide item id.", "warn");
      return;
    }
    adjustQuantity(itemId, inc);
  });

  U.byId("refresh-btn").addEventListener("click", loadCart);

  loadCart();
})();
