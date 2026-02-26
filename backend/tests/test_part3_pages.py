from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class Part3PageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_required_pages_render(self):
        for path in ["/products/", "/search/", "/contact/", "/about/", "/admin-panel/", "/order-confirmation/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_required_pages_include_seo_and_accessibility_basics(self):
        for path in ["/", "/products/", "/cart/", "/checkout/", "/search/", "/contact/", "/about/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                body = response.content.decode("utf-8")
                self.assertIn('name="description"', body)
                self.assertIn('class="skip-link"', body)
                self.assertIn("<h1", body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_contact_support_endpoint(self):
        response = self.client.post(
            "/api/support/contact/",
            {
                "name": "Tester",
                "email": "tester@example.com",
                "subject": "Need help",
                "message": "Please assist with my order.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_contact_support_requires_fields(self):
        response = self.client.post("/api/support/contact/", {"name": "A"}, format="json")
        self.assertEqual(response.status_code, 400)
