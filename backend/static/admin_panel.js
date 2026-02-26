(function () {
  const U = window.ShopUI;

  function status(text, tone) {
    U.setStatus("admin-status", text, tone || "info");
  }

  async function loadUsers() {
    const users = await U.request(U.API + "/auth/admin/users/", { auth: true, guest: false });
    U.byId("users-json").textContent = JSON.stringify(users, null, 2);
  }

  async function loadRefunds() {
    const refunds = await U.request(U.API + "/commerce/admin/refunds/", { auth: true, guest: false });
    U.byId("refunds-json").textContent = JSON.stringify(refunds, null, 2);
  }

  async function loadDelivery() {
    const options = await U.request(U.API + "/commerce/admin/delivery-options/", { auth: true, guest: false });
    U.byId("delivery-json").textContent = JSON.stringify(options, null, 2);
  }

  async function createDelivery() {
    const body = {
      code: U.byId("delivery-code").value.trim(),
      label: U.byId("delivery-label").value.trim(),
      cost: U.byId("delivery-cost").value.trim() || "0.00",
      is_active: true,
    };
    await U.request(U.API + "/commerce/admin/delivery-options/", {
      method: "POST",
      auth: true,
      guest: false,
      body,
    });
    await loadDelivery();
    status("Delivery option created.", "ok");
  }

  async function runBulkUpload() {
    const body = {
      format: U.byId("bulk-format").value,
      payload: U.byId("bulk-payload").value,
    };
    const result = await U.request(U.API + "/catalog/admin/products/bulk-upload/", {
      method: "POST",
      auth: true,
      guest: false,
      body,
    });
    status(`Bulk upload done. Created ${result.created}, updated ${result.updated}, failed ${result.failed}.`, "ok");
  }

  async function init() {
    try {
      await Promise.all([loadUsers(), loadRefunds(), loadDelivery()]);
      status("Admin data loaded.", "info");
    } catch (err) {
      status(U.errorText(err), "error");
    }
  }

  U.byId("users-refresh-btn").addEventListener("click", () => loadUsers().catch((err) => status(U.errorText(err), "error")));
  U.byId("refunds-refresh-btn").addEventListener("click", () => loadRefunds().catch((err) => status(U.errorText(err), "error")));
  U.byId("delivery-refresh-btn").addEventListener("click", () => loadDelivery().catch((err) => status(U.errorText(err), "error")));
  U.byId("delivery-create-btn").addEventListener("click", () => createDelivery().catch((err) => status(U.errorText(err), "error")));
  U.byId("bulk-upload-btn").addEventListener("click", () => runBulkUpload().catch((err) => status(U.errorText(err), "error")));

  init();
})();
