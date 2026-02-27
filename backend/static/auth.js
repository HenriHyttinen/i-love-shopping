(function () {
  const U = window.ShopUI;

  function byId(id) {
    return document.getElementById(id);
  }

  async function refreshAuthNav() {
    const guest = byId("nav-guest");
    const member = byId("nav-member");
    const name = byId("nav-user-name");
    const logoutBtn = byId("nav-logout");

    if (guest) guest.style.display = "none";
    if (member) member.style.display = "none";

    // Optimistic render from local token first to avoid perceived nav lag.
    const hasToken = !!U.getAccessToken();
    if (guest) guest.style.display = hasToken ? "none" : "inline-flex";
    if (member) member.style.display = hasToken ? "inline-flex" : "none";

    const user = await U.fetchCurrentUser();
    const isAuth = !!user;

    if (guest) guest.style.display = isAuth ? "none" : "inline-flex";
    if (member) member.style.display = isAuth ? "inline-flex" : "none";
    if (name) name.textContent = isAuth ? user.full_name || user.email : "";

    if (logoutBtn) {
      logoutBtn.onclick = async function () {
        U.setAccessToken("");
        await refreshAuthNav();
        if (location.pathname === "/account/" || location.pathname === "/orders/") {
          location.href = "/login/";
        }
      };
    }
  }

  window.ShopAuth = {
    refreshAuthNav,
  };
})();
