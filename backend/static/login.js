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
      let me = null;
      if (window.ShopAuth) await window.ShopAuth.refreshAuthNav();
      try {
        me = await U.fetchCurrentUser();
      } catch (_) {
        me = null;
      }
      U.setStatus("login-status", "Login successful.", "ok");
      const providedNext = U.byId("next").value.trim();
      const defaultNext = me && me.is_staff ? "/admin-panel/" : "/account/";
      const next = providedNext || defaultNext;
      setTimeout(() => {
        location.href = next;
      }, 300);
    } catch (err) {
      U.setStatus("login-status", U.errorText(err), "error");
    }
  }

  U.byId("login-btn").addEventListener("click", login);
  if (window.ShopAuth) window.ShopAuth.refreshAuthNav();
})();
