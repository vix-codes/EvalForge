import hashlib
import hmac
import secrets


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()  # hmac.new is the correct call for Python's hmac module
    return hmac.compare_digest(expected, signature)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def constant_time_compare(val1: str, val2: str) -> bool:
    return hmac.compare_digest(val1.encode(), val2.encode())
