import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


class EncryptedTextField(models.TextField):
    _PREFIX = "enc::"

    def _build_fernet(self) -> Fernet:
        configured_key = getattr(settings, "USER_DATA_ENCRYPTION_KEY", "").strip()
        if not configured_key:
            configured_key = getattr(settings, "COMMERCE_ENCRYPTION_KEY", "").strip()
        if configured_key:
            return Fernet(configured_key.encode("utf-8"))
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _encrypt(self, value: str) -> str:
        token = self._build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{self._PREFIX}{token}"

    def _decrypt(self, value: str) -> str:
        if not value.startswith(self._PREFIX):
            return value
        token = value[len(self._PREFIX) :]
        try:
            return self._build_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return value

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return self._decrypt(value)

    def to_python(self, value):
        if value in (None, "") or not isinstance(value, str):
            return value
        return self._decrypt(value)

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        if isinstance(value, str) and value.startswith(self._PREFIX):
            return value
        return self._encrypt(str(value))
