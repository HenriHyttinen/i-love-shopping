(function () {
  const U = window.ShopUI;

  function status(text, tone) {
    U.setStatus("admin-status", text, tone || "info");
  }

  async function loadUsers() {
    const users = await U.request(U.API + "/auth/admin/users/", { auth: true, guest: false });
    U.byId("users-json").textContent = JSON.stringify(users, null, 2);
  }

  async function updateUserRole() {
    const userId = Number(U.byId("user-role-id").value);
    const role = U.byId("user-role-value").value;
    if (!userId) throw { detail: "Provide user ID." };
    await U.request(U.API + `/auth/admin/users/${userId}/role/`, {
      method: "POST",
      auth: true,
      guest: false,
      body: { role },
    });
    await loadUsers();
    status("User role updated.", "ok");
  }

  async function loadRefunds() {
    const refunds = await U.request(U.API + "/commerce/admin/refunds/", { auth: true, guest: false });
    U.byId("refunds-json").textContent = JSON.stringify(refunds, null, 2);
  }

  async function updateRefundStatus() {
    const refundId = Number(U.byId("refund-id-admin").value);
    const update = {
      status: U.byId("refund-status-admin").value,
      note: U.byId("refund-note-admin").value.trim(),
    };
    if (!refundId) throw { detail: "Provide refund ID." };
    await U.request(U.API + `/commerce/admin/refunds/${refundId}/status/`, {
      method: "POST",
      auth: true,
      guest: false,
      body: update,
    });
    await loadRefunds();
    status("Refund status updated.", "ok");
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

  async function loadCategories() {
    const categories = await U.request(U.API + "/catalog/admin/categories/", { auth: true, guest: false });
    U.byId("categories-json").textContent = JSON.stringify(categories, null, 2);
  }

  async function createCategory() {
    const body = {
      name: U.byId("category-name").value.trim(),
      slug: U.byId("category-slug").value.trim(),
    };
    await U.request(U.API + "/catalog/admin/categories/", {
      method: "POST",
      auth: true,
      guest: false,
      body,
    });
    await loadCategories();
    status("Category created.", "ok");
  }

  async function updateCategory() {
    const categoryId = Number(U.byId("category-id").value);
    if (!categoryId) throw { detail: "Provide category ID." };
    const body = {
      name: U.byId("category-name").value.trim(),
      slug: U.byId("category-slug").value.trim(),
    };
    await U.request(U.API + `/catalog/admin/categories/${categoryId}/`, {
      method: "PATCH",
      auth: true,
      guest: false,
      body,
    });
    await loadCategories();
    status("Category updated.", "ok");
  }

  async function deleteCategory() {
    const categoryId = Number(U.byId("category-id").value);
    if (!categoryId) throw { detail: "Provide category ID." };
    await U.request(U.API + `/catalog/admin/categories/${categoryId}/`, {
      method: "DELETE",
      auth: true,
      guest: false,
      json: false,
    });
    await loadCategories();
    status("Category deleted.", "ok");
  }

  async function loadProducts() {
    const products = await U.request(U.API + "/catalog/admin/products/", { auth: true, guest: false });
    U.byId("products-json").textContent = JSON.stringify(products, null, 2);
  }

  function productPayload() {
    return {
      name: U.byId("product-name-admin").value.trim(),
      description: U.byId("product-name-admin").value.trim(),
      price: U.byId("product-price-admin").value.trim(),
      stock_quantity: Number(U.byId("product-stock-admin").value || 0),
      category: Number(U.byId("product-category-admin").value || 0),
      brand: Number(U.byId("product-brand-admin").value || 0),
      is_active: true,
      weight_kg: "1.00",
      weight_lb: "2.20",
      length_cm: "20.00",
      width_cm: "10.00",
      height_cm: "5.00",
      length_in: "7.87",
      width_in: "3.94",
      height_in: "1.97",
    };
  }

  async function createProduct() {
    const body = productPayload();
    if (!body.name || !body.category || !body.brand) throw { detail: "Provide product name, category ID, and brand ID." };
    await U.request(U.API + "/catalog/admin/products/", {
      method: "POST",
      auth: true,
      guest: false,
      body,
    });
    await loadProducts();
    status("Product created.", "ok");
  }

  async function updateProduct() {
    const productId = Number(U.byId("product-id-admin").value);
    if (!productId) throw { detail: "Provide product ID." };
    const body = productPayload();
    await U.request(U.API + `/catalog/admin/products/${productId}/`, {
      method: "PATCH",
      auth: true,
      guest: false,
      body,
    });
    await loadProducts();
    status("Product updated.", "ok");
  }

  async function deleteProduct() {
    const productId = Number(U.byId("product-id-admin").value);
    if (!productId) throw { detail: "Provide product ID." };
    await U.request(U.API + `/catalog/admin/products/${productId}/`, {
      method: "DELETE",
      auth: true,
      guest: false,
      json: false,
    });
    await loadProducts();
    status("Product deleted.", "ok");
  }

  async function loadOrders() {
    const orders = await U.request(U.API + "/commerce/admin/orders/", { auth: true, guest: false });
    U.byId("orders-json-admin").textContent = JSON.stringify(orders, null, 2);
  }

  async function updateOrderStatus() {
    const orderId = Number(U.byId("order-id-admin").value);
    if (!orderId) throw { detail: "Provide order ID." };
    const body = {
      status: U.byId("order-status-admin").value,
      note: U.byId("order-note-admin").value.trim(),
    };
    await U.request(U.API + `/commerce/admin/orders/${orderId}/status/`, {
      method: "POST",
      auth: true,
      guest: false,
      body,
    });
    await loadOrders();
    status("Order status updated.", "ok");
  }

  async function deleteReview() {
    const reviewId = Number(U.byId("review-id-admin").value);
    if (!reviewId) throw { detail: "Provide review ID." };
    await U.request(U.API + `/catalog/admin/reviews/${reviewId}/`, {
      method: "DELETE",
      auth: true,
      guest: false,
      json: false,
    });
    status("Review deleted.", "ok");
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
      await Promise.all([loadUsers(), loadRefunds(), loadDelivery(), loadCategories(), loadProducts(), loadOrders()]);
      status("Admin data loaded.", "info");
    } catch (err) {
      status(U.errorText(err), "error");
    }
  }

  U.byId("users-refresh-btn").addEventListener("click", () => loadUsers().catch((err) => status(U.errorText(err), "error")));
  U.byId("user-role-update-btn").addEventListener("click", () => updateUserRole().catch((err) => status(U.errorText(err), "error")));

  U.byId("refunds-refresh-btn").addEventListener("click", () => loadRefunds().catch((err) => status(U.errorText(err), "error")));
  U.byId("refund-status-update-btn").addEventListener("click", () => updateRefundStatus().catch((err) => status(U.errorText(err), "error")));

  U.byId("delivery-refresh-btn").addEventListener("click", () => loadDelivery().catch((err) => status(U.errorText(err), "error")));
  U.byId("delivery-create-btn").addEventListener("click", () => createDelivery().catch((err) => status(U.errorText(err), "error")));

  U.byId("category-refresh-btn").addEventListener("click", () => loadCategories().catch((err) => status(U.errorText(err), "error")));
  U.byId("category-create-btn").addEventListener("click", () => createCategory().catch((err) => status(U.errorText(err), "error")));
  U.byId("category-update-btn").addEventListener("click", () => updateCategory().catch((err) => status(U.errorText(err), "error")));
  U.byId("category-delete-btn").addEventListener("click", () => deleteCategory().catch((err) => status(U.errorText(err), "error")));

  U.byId("product-refresh-btn").addEventListener("click", () => loadProducts().catch((err) => status(U.errorText(err), "error")));
  U.byId("product-create-btn").addEventListener("click", () => createProduct().catch((err) => status(U.errorText(err), "error")));
  U.byId("product-update-btn").addEventListener("click", () => updateProduct().catch((err) => status(U.errorText(err), "error")));
  U.byId("product-delete-btn").addEventListener("click", () => deleteProduct().catch((err) => status(U.errorText(err), "error")));

  U.byId("orders-refresh-btn").addEventListener("click", () => loadOrders().catch((err) => status(U.errorText(err), "error")));
  U.byId("order-status-update-btn").addEventListener("click", () => updateOrderStatus().catch((err) => status(U.errorText(err), "error")));

  U.byId("review-delete-btn").addEventListener("click", () => deleteReview().catch((err) => status(U.errorText(err), "error")));
  U.byId("bulk-upload-btn").addEventListener("click", () => runBulkUpload().catch((err) => status(U.errorText(err), "error")));

  init();
})();
