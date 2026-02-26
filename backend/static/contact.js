(function () {
  const U = window.ShopUI;

  async function submitContact() {
    const payload = {
      name: U.byId("contact-name").value.trim(),
      email: U.byId("contact-email").value.trim(),
      subject: U.byId("contact-subject").value.trim(),
      message: U.byId("contact-message").value.trim(),
    };
    try {
      await U.request(U.API + "/support/contact/", {
        method: "POST",
        guest: false,
        body: payload,
      });
      U.byId("contact-message").value = "";
      U.setStatus("contact-status", "Support request sent.", "ok");
    } catch (err) {
      U.setStatus("contact-status", U.errorText(err), "error");
    }
  }

  U.byId("contact-send-btn").addEventListener("click", submitContact);
})();
