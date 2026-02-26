from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


class TokenBucketRateLimitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    @override_settings(
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_CAPACITY=2,
        RATE_LIMIT_REFILL_RATE=0.0001,
    )
    def test_token_bucket_blocks_after_capacity(self):
        first = self.client.get("/api/catalog/products/")
        second = self.client.get("/api/catalog/products/")
        third = self.client.get("/api/catalog/products/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)
        self.assertIn("Retry-After", third)

    @override_settings(
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_CAPACITY=1,
        RATE_LIMIT_REFILL_RATE=0.0001,
    )
    def test_non_api_route_not_rate_limited(self):
        first = self.client.get("/about/")
        second = self.client.get("/about/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
