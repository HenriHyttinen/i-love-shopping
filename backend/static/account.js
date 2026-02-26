(function () {
  const U = window.ShopUI;

  async function loadAccount() {
    try {
      if (window.ShopAuth) await window.ShopAuth.refreshAuthNav();
      const user = await U.fetchCurrentUser();
      if (!user) {
        location.href = "/login/?next=/account/";
        return;
      }
      U.byId("acc-name").textContent = user.full_name || "-";
      U.byId("acc-email").textContent = user.email || "-";
      U.byId("acc-role").textContent = user.role || (user.is_staff ? "staff" : "customer");
      const adminBtn = U.byId("go-admin-panel");
      if (adminBtn && user.is_staff) {
        adminBtn.style.display = "inline-block";
      }
      U.setStatus("account-status", "Account loaded.", "ok");
    } catch (err) {
      U.setStatus("account-status", JSON.stringify(err), "error");
    }
  }

  U.byId("go-orders").addEventListener("click", () => {
    location.href = "/orders/";
  });
  U.byId("go-checkout-guest").addEventListener("click", () => {
    location.href = "/checkout/";
  });
  const adminBtn = U.byId("go-admin-panel");
  if (adminBtn) {
    adminBtn.addEventListener("click", () => {
      location.href = "/admin-panel/";
    });
  }

  loadAccount();
})();
