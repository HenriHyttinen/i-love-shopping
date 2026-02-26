import math
import time
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


class TokenBucketRateLimitMiddleware:
    """
    Lightweight token-bucket limiter for API endpoints.
    Keyed by authenticated user id when available, otherwise client IP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", False):
            return self.get_response(request)

        scope_prefixes = getattr(settings, "RATE_LIMIT_SCOPE_PREFIXES", ("/api/",))
        if not any(request.path.startswith(prefix) for prefix in scope_prefixes):
            return self.get_response(request)

        capacity = int(getattr(settings, "RATE_LIMIT_CAPACITY", 120))
        refill_rate = float(getattr(settings, "RATE_LIMIT_REFILL_RATE", 2.0))
        if capacity <= 0 or refill_rate <= 0:
            return self.get_response(request)

        identifier = self._identifier(request)
        cache_key = f"token_bucket:{identifier}"
        now = time.time()
        bucket = cache.get(cache_key) or {"tokens": float(capacity), "last": now}

        elapsed = max(0.0, now - float(bucket.get("last", now)))
        tokens = min(float(capacity), float(bucket.get("tokens", capacity)) + elapsed * refill_rate)

        if tokens < 1.0:
            wait_seconds = max(1, math.ceil((1.0 - tokens) / refill_rate))
            response = JsonResponse(
                {"detail": "Rate limit exceeded. Please retry shortly."},
                status=429,
            )
            response["Retry-After"] = str(wait_seconds)
            response["X-RateLimit-Limit"] = str(capacity)
            response["X-RateLimit-Remaining"] = "0"
            return response

        tokens -= 1.0
        cache.set(cache_key, {"tokens": tokens, "last": now}, timeout=3600)

        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(capacity)
        response["X-RateLimit-Remaining"] = str(max(0, int(tokens)))
        return response

    def _identifier(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()
            if raw_token:
                digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]
                return f"token:{digest}"

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return f"ip:{ip}"
