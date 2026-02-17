(function () {
  const U = window.ShopUI;
  let recaptchaSiteKey = "";
  let recaptchaWidgetId = null;

  async function loadRecaptchaSiteKey() {
    try {
      const data = await U.request(U.API + "/auth/recaptcha-site-key/", { guest: false });
      recaptchaSiteKey = data.site_key || "";
      tryRenderRecaptcha();
    } catch (_) {
      // keep fallback available in dev
    }
  }

  function tryRenderRecaptcha() {
    if (!recaptchaSiteKey || !window.grecaptcha || recaptchaWidgetId !== null) return;
    recaptchaWidgetId = window.grecaptcha.render("recaptcha-container", { sitekey: recaptchaSiteKey });
  }

  async function register() {
    try {
      const fullName = U.byId("full_name").value.trim();
      const email = U.byId("email").value.trim();
      const password = U.byId("password").value;
      const recaptcha =
        window.grecaptcha && recaptchaWidgetId !== null
          ? window.grecaptcha.getResponse(recaptchaWidgetId)
          : "";

      if (!fullName || !email || !password) {
        U.setStatus("register-status", "Full name, email and password are required.", "warn");
        return;
      }
      if (recaptchaSiteKey && !recaptcha) {
        U.setStatus("register-status", "Please complete reCAPTCHA.", "warn");
        return;
      }

      const data = await U.request(U.API + "/auth/register/", {
        method: "POST",
        guest: false,
        body: {
          full_name: fullName,
          email,
          password,
          recaptcha_token: recaptcha || "ok",
        },
      });
      U.setAccessToken(data.access || "");
      if (window.ShopAuth) await window.ShopAuth.refreshAuthNav();
      U.setStatus("register-status", "Registration successful.", "ok");
      setTimeout(() => {
        location.href = "/account/";
      }, 300);
    } catch (err) {
      U.setStatus("register-status", JSON.stringify(err), "error");
    }
  }

  window.onRecaptchaLoaded = function () {
    tryRenderRecaptcha();
  };

  U.byId("register-btn").addEventListener("click", register);
  if (window.ShopAuth) window.ShopAuth.refreshAuthNav();
  loadRecaptchaSiteKey();
})();
