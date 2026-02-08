(function () {
  const U = window.ShopUI;

  async function login() {
    try {
      const email = U.byId("auth-email").value.trim();
      const password = U.byId("auth-password").value;
      const data = await U.request(U.API + "/auth/login/", {
        method: "POST",
        guest: false,
        body: { email, password },
      });
      U.setAccessToken(data.access);
      U.setStatus("orders-status", "Logged in.", "ok");
    } catch (err) {
      U.setStatus("orders-status", JSON.stringify(err), "error");
    }
  }

  function renderList(items) {
    const root = U.byId("orders-list");
    if (!items.length) {
      root.innerHTML = "<div class='muted'>No orders found.</div>";
      return;
    }
    root.innerHTML = items
      .map(
        (o) => `
          <article class="panel">
            <div class="grid">
              <div><strong>Order #${o.id}</strong></div>
              <div><span class="badge">${U.esc(o.status)}</span></div>
              <div>Total ${U.fmtMoney(o.total)}</div>
              <div>${new Date(o.created_at).toLocaleString()}</div>
            </div>
            <div class="btn-row" style="margin-top:10px">
              <button class="secondary" data-open="${o.id}">Details</button>
              <button class="danger" data-cancel="${o.id}">Cancel</button>
            </div>
          </article>
        `
      )
      .join("");

    root.querySelectorAll("button[data-open]").forEach((btn) => {
      btn.addEventListener("click", () => loadDetails(Number(btn.getAttribute("data-open"))));
    });
    root.querySelectorAll("button[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", () => cancelOrder(Number(btn.getAttribute("data-cancel"))));
    });
  }

  async function loadOrders() {
    try {
      const params = new URLSearchParams();
      const status = U.byId("status").value;
      const dateFrom = U.byId("date_from").value.trim();
      const dateTo = U.byId("date_to").value.trim();
      if (status) params.append("status", status);
      if (dateFrom) params.append("date_from", dateFrom);
      if (dateTo) params.append("date_to", dateTo);
      const list = await U.request(U.API + "/commerce/orders/?" + params.toString(), { auth: true });
      U.byId("orders-json").textContent = JSON.stringify(list, null, 2);
      renderList(list);
      U.setStatus("orders-status", list.length + " orders loaded.", "info");
    } catch (err) {
      U.setStatus("orders-status", JSON.stringify(err), "error");
    }
  }

  async function loadDetails(orderId) {
    try {
      const detail = await U.request(U.API + "/commerce/orders/" + orderId + "/", { auth: true });
      U.byId("orders-json").textContent = JSON.stringify(detail, null, 2);
      U.setStatus("orders-status", "Order #" + orderId + " loaded.", "info");
    } catch (err) {
      U.setStatus("orders-status", JSON.stringify(err), "error");
    }
  }

  async function cancelOrder(orderId) {
    try {
      const data = await U.request(U.API + "/commerce/orders/" + orderId + "/cancel/", {
        method: "POST",
        auth: true,
        body: {},
      });
      U.setStatus("orders-status", data.detail || "Cancelled", "ok");
      loadOrders();
    } catch (err) {
      U.setStatus("orders-status", JSON.stringify(err), "error");
    }
  }

  U.byId("auth-login-btn").addEventListener("click", login);
  U.byId("load-orders-btn").addEventListener("click", loadOrders);

  loadOrders();
})();
