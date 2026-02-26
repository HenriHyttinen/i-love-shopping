import hashlib


def hash_token_identifier(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
