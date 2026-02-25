from __future__ import annotations

import re
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


def _clean_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _norm(value)).strip()


US_STATE_TO_ABBR = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

US_ZIP_FIRST_DIGIT_ALLOWED_STATES = {
    "0": {"CT", "MA", "ME", "NH", "NJ", "PR", "RI", "VT"},
    "1": {"DE", "NY", "PA"},
    "2": {"DC", "MD", "NC", "SC", "VA", "WV"},
    "3": {"AL", "FL", "GA", "MS", "TN"},
    "4": {"IN", "KY", "MI", "OH"},
    "5": {"IA", "MN", "MT", "ND", "SD", "WI"},
    "6": {"IL", "KS", "MO", "NE"},
    "7": {"AR", "LA", "OK", "TX"},
    "8": {"AZ", "CO", "ID", "NM", "NV", "UT", "WY"},
    "9": {"AK", "CA", "HI", "OR", "WA"},
}


def _normalize_us_state(value: str) -> str:
    state_norm = _clean_text(value)
    if len(state_norm) == 2 and state_norm.isalpha():
        return state_norm.upper()
    return US_STATE_TO_ABBR.get(state_norm, "")


def _us_city_matches(input_city: str, reference_city: str) -> bool:
    left = _clean_text(input_city)
    right = _clean_text(reference_city)
    return bool(left and right and (left == right or left in right or right in left))


def _bool_env(value, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _country_requires_state(country: str) -> bool:
    country_norm = _norm(country)
    return country_norm in {
        "us",
        "usa",
        "united states",
        "united states of america",
        "fi",
        "finland",
        "suomi",
        "ca",
        "canada",
        "au",
        "australia",
    }


def _finnish_address_consistency_check(*, city: str, state: str, postal: str, country: str) -> AddressValidationResult:
    country_norm = _norm(country)
    if country_norm not in {"fi", "finland", "suomi"}:
        return AddressValidationResult(ok=True)

    if len(postal) != 5 or not postal.isdigit():
        return AddressValidationResult(ok=False, detail="For Finland, postal_code must be a 5-digit code.")

    city_norm = _norm(city)
    state_norm = _norm(state)
    city_expected_by_prefix = {
        "00": "helsinki",
        "01": "vantaa",
        "02": "espoo",
    }
    expected_city = city_expected_by_prefix.get(postal[:2])
    if expected_city and expected_city not in city_norm:
        return AddressValidationResult(ok=False, detail="Shipping address city does not match postal code.")

    # City-level municipalities should use region in the state field for these common Uusimaa cities.
    if city_norm in {"helsinki", "espoo", "vantaa"} and state_norm != "uusimaa":
        return AddressValidationResult(ok=False, detail="For this Finnish city, state should be Uusimaa.")

    return AddressValidationResult(ok=True)


def _local_address_sanity_check(address: dict) -> AddressValidationResult:
    line1 = str(address.get("line1", "")).strip()
    city = str(address.get("city", "")).strip()
    state = str(address.get("state", "")).strip()
    postal = str(address.get("postal_code", "")).strip()
    country = str(address.get("country", "")).strip()

    if len(line1) < 5 or len(city) < 2 or len(postal) < 3 or len(country) < 2:
        return AddressValidationResult(ok=False, detail="Shipping address appears incomplete or inaccurate.")
    if _country_requires_state(country) and len(state) < 2:
        return AddressValidationResult(ok=False, detail="Shipping address appears incomplete or inaccurate.")

    if not any(ch.isalpha() for ch in line1):
        return AddressValidationResult(ok=False, detail="Shipping address line is not valid.")

    if not any(ch.isdigit() for ch in line1):
        return AddressValidationResult(ok=False, detail="Shipping address line should include a building number.")

    invalid_markers = {"unknown", "nowhere", "n/a", "na", "test", "dummy"}
    combined = f"{line1} {city} {state} {country}".lower()
    if any(marker in combined for marker in invalid_markers):
        return AddressValidationResult(ok=False, detail="Shipping address appears to use placeholder values.")

    fi_check = _finnish_address_consistency_check(
        city=city,
        state=state,
        postal=postal,
        country=country,
    )
    if not fi_check.ok:
        return fi_check

    return AddressValidationResult(ok=True)


def _us_zip_consistency_check(*, city: str, state: str, postal: str, strict: bool) -> AddressValidationResult:
    zip_match = re.match(r"^(\d{5})(?:-\d{4})?$", postal.strip())
    if not zip_match:
        return AddressValidationResult(ok=False, detail="For US addresses, postal_code must be ZIP format 12345 or 12345-6789.")

    zipcode = zip_match.group(1)
    state_abbr = _normalize_us_state(state)
    if not state_abbr:
        return AddressValidationResult(ok=False, detail="For US addresses, state must be a valid state code or name.")

    allowed_states = US_ZIP_FIRST_DIGIT_ALLOWED_STATES.get(zipcode[0], set())
    if allowed_states and state_abbr not in allowed_states:
        return AddressValidationResult(ok=False, detail="Shipping address state does not match postal code region.")

    try:
        resp = requests.get(
            f"https://api.zippopotam.us/us/{zipcode}",
            timeout=3,
        )
        if resp.status_code == 404:
            return AddressValidationResult(ok=False, detail="Shipping address postal code could not be verified.")
        if resp.status_code != 200:
            if strict:
                return AddressValidationResult(ok=False, detail="Address validation service unavailable.")
            return AddressValidationResult(ok=True)
        payload = resp.json() or {}
    except Exception:
        if strict:
            return AddressValidationResult(ok=False, detail="Address validation service unavailable.")
        return AddressValidationResult(ok=True)

    places = payload.get("places") or []
    if not places:
        return AddressValidationResult(ok=False, detail="Shipping address postal code could not be verified.")

    city_ok = False
    state_ok = False
    for place in places:
        city_name = str(place.get("place name", "")).strip()
        place_state = str(place.get("state abbreviation", "")).strip().upper()
        if place_state and place_state == state_abbr:
            state_ok = True
            if _us_city_matches(city, city_name):
                city_ok = True
                break

    if not state_ok:
        return AddressValidationResult(ok=False, detail="Shipping address state does not match postal code.")
    if not city_ok:
        return AddressValidationResult(ok=False, detail="Shipping address city does not match postal code.")

    return AddressValidationResult(ok=True)


def validate_shipping_address_accuracy(address: dict) -> AddressValidationResult:
    enabled = _bool_env(getattr(settings, "ADDRESS_VALIDATION_ENABLED", True), True)
    strict = _bool_env(getattr(settings, "ADDRESS_VALIDATION_STRICT", False), False)
    if not enabled:
        return AddressValidationResult(ok=True)

    country_norm = _norm(address.get("country", ""))
    if country_norm in {"us", "usa", "united states", "united states of america"}:
        us_check = _us_zip_consistency_check(
            city=str(address.get("city", "")).strip(),
            state=str(address.get("state", "")).strip(),
            postal=str(address.get("postal_code", "")).strip(),
            strict=strict,
        )
        if not us_check.ok:
            return us_check

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
    input_state = str(address.get("state", "")).strip()
    state_ok = True
    if input_state:
        state_ok = _contains(input_state, props.get("state", "") or props.get("state_code", ""))
    postal_ok = _contains(address.get("postal_code", ""), props.get("postcode", ""))
    country_input = _norm(address.get("country", ""))
    country_code = _norm(props.get("country_code", ""))
    country_name = _norm(props.get("country", ""))
    country_ok = bool(country_input and (country_input == country_code or country_input == country_name))

    if not (city_ok and state_ok and postal_ok and country_ok):
        return AddressValidationResult(ok=False, detail="Shipping address does not match verified location.")

    return AddressValidationResult(ok=True)
