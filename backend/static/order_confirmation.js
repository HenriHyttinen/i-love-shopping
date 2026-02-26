(function () {
  const U = window.ShopUI;
  const raw = localStorage.getItem("last_order_confirmation");
  const content = U.byId("confirm-content");
  const status = U.byId("confirm-status");

  if (!raw) {
    U.setStatus("confirm-status", "No order confirmation found.", "warn");
    content.innerHTML = "<p>Please place an order first from checkout.</p>";
    return;
  }

  let data = null;
  try {
    data = JSON.parse(raw);
  } catch (_) {
    U.setStatus("confirm-status", "Order confirmation payload is invalid.", "error");
    return;
  }

  const order = data.order || {};
  const payment = data.payment || {};
  const shippingOption = String(order.shipping_option || "standard").toLowerCase();
  const estimate = shippingOption === "express" ? "1-3 business days" : "3-7 business days";
  const paymentOk = payment.status === "success";

  U.setStatus("confirm-status", paymentOk ? "Order completed successfully." : "Order was created but payment failed.", paymentOk ? "ok" : "warn");
  content.innerHTML = `
    <p><strong>Order ID:</strong> ${U.esc(order.id || "-")}</p>
    <p><strong>Reference Number:</strong> ${U.esc(order.tracking_code || "pending")}</p>
    <p><strong>Order Status:</strong> ${U.esc(order.status || "-")}</p>
    <p><strong>Payment Status:</strong> ${U.esc(payment.status || "-")}</p>
    <p><strong>Estimated Delivery:</strong> ${estimate}</p>
    <p><strong>Total:</strong> ${U.fmtMoney(order.total || 0)}</p>
    <div class="btn-row" style="margin-top:10px;">
      <a class="btn-link" href="/orders/">Open My Orders</a>
      <a class="btn-link" href="/products/">Continue Shopping</a>
    </div>
  `;
})();
