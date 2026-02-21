from __future__ import annotations

from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass
class AddressValidationResult:
    ok: bool
    detail: str = ""


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _contains(left: str, right: str) -> bool:
    a = _norm(left)
    b = _norm(right)
    return bool(a and b and (a in b or b in a))


def _bool_env(value, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _local_address_sanity_check(address: dict) -> AddressValidationResult:
    line1 = str(address.get("line1", "")).strip()
    city = str(address.get("city", "")).strip()
    state = str(address.get("state", "")).strip()
    postal = str(address.get("postal_code", "")).strip()
    country = str(address.get("country", "")).strip()

    if len(line1) < 5 or len(city) < 2 or len(state) < 2 or len(postal) < 3 or len(country) < 2:
        return AddressValidationResult(ok=False, detail="Shipping address appears incomplete or inaccurate.")

    if not any(ch.isalpha() for ch in line1):
        return AddressValidationResult(ok=False, detail="Shipping address line is not valid.")

    if not any(ch.isdigit() for ch in line1):
        return AddressValidationResult(ok=False, detail="Shipping address line should include a building number.")

    invalid_markers = {"unknown", "nowhere", "n/a", "na", "test", "dummy"}
    combined = f"{line1} {city} {state} {country}".lower()
    if any(marker in combined for marker in invalid_markers):
        return AddressValidationResult(ok=False, detail="Shipping address appears to use placeholder values.")

    return AddressValidationResult(ok=True)


def validate_shipping_address_accuracy(address: dict) -> AddressValidationResult:
    enabled = _bool_env(getattr(settings, "ADDRESS_VALIDATION_ENABLED", True), True)
    strict = _bool_env(getattr(settings, "ADDRESS_VALIDATION_STRICT", False), False)
    if not enabled:
        return AddressValidationResult(ok=True)

    api_key = (getattr(settings, "GEOAPIFY_API_KEY", "") or "").strip()
    if not api_key:
        return _local_address_sanity_check(address)

    text = ", ".join(
        [
            str(address.get("line1", "")).strip(),
            str(address.get("city", "")).strip(),
            str(address.get("state", "")).strip(),
            str(address.get("postal_code", "")).strip(),
            str(address.get("country", "")).strip(),
        ]
    )
    try:
        resp = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={
                "text": text,
                "limit": 1,
                "apiKey": api_key,
            },
            timeout=4,
        )
        if resp.status_code != 200:
            if strict:
                return AddressValidationResult(ok=False, detail="Address validation service unavailable.")
            return _local_address_sanity_check(address)
        payload = resp.json() or {}
    except Exception:
        if strict:
            return AddressValidationResult(ok=False, detail="Address validation service unavailable.")
        return _local_address_sanity_check(address)

    features = payload.get("features") or []
    if not features:
        return AddressValidationResult(ok=False, detail="Could not verify shipping address.")

    props = (features[0] or {}).get("properties") or {}
    min_confidence = float(getattr(settings, "ADDRESS_VALIDATION_MIN_CONFIDENCE", 0.75))
    confidence = float(props.get("rank", {}).get("confidence", 0.0))
    if confidence < min_confidence:
        return AddressValidationResult(ok=False, detail="Shipping address confidence is too low.")

    city_ok = _contains(address.get("city", ""), props.get("city", ""))
    state_ok = _contains(address.get("state", ""), props.get("state", "") or props.get("state_code", ""))
    postal_ok = _contains(address.get("postal_code", ""), props.get("postcode", ""))
    country_input = _norm(address.get("country", ""))
    country_code = _norm(props.get("country_code", ""))
    country_name = _norm(props.get("country", ""))
    country_ok = bool(country_input and (country_input == country_code or country_input == country_name))

    if not (city_ok and state_ok and postal_ok and country_ok):
        return AddressValidationResult(ok=False, detail="Shipping address does not match verified location.")

    return AddressValidationResult(ok=True)
