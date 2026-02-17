(function () {
  const U = window.ShopUI;

  async function login() {
    try {
      const email = U.byId("email").value.trim();
      const password = U.byId("password").value;
      if (!email || !password) {
        U.setStatus("login-status", "Email and password are required.", "warn");
        return;
      }
      const data = await U.request(U.API + "/auth/login/", {
        method: "POST",
        guest: false,
        body: { email, password },
      });
      U.setAccessToken(data.access);
      if (window.ShopAuth) await window.ShopAuth.refreshAuthNav();
      U.setStatus("login-status", "Login successful.", "ok");
      const next = U.byId("next").value.trim() || "/account/";
      setTimeout(() => {
        location.href = next;
      }, 300);
    } catch (err) {
      U.setStatus("login-status", JSON.stringify(err), "error");
    }
  }

  U.byId("login-btn").addEventListener("click", login);
  if (window.ShopAuth) window.ShopAuth.refreshAuthNav();
})();
