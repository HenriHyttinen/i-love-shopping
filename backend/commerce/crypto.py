import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings


def _build_fernet() -> Fernet:
    configured_key = getattr(settings, "COMMERCE_ENCRYPTION_KEY", "").strip()
    if configured_key:
        return Fernet(configured_key.encode("utf-8"))
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_json(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return _build_fernet().encrypt(payload).decode("utf-8")


def decrypt_json(token: str) -> dict:
    if not token:
        return {}
    raw = _build_fernet().decrypt(token.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))
