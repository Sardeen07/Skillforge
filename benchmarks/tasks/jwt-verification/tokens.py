import base64
import hashlib
import hmac
import json
import time

SECRET = b"change-me-in-production"


class InvalidToken(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def encode_token(claims: dict) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps(claims).encode())
    sig = hmac.new(SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(sig)}"


def decode_token(token: str) -> dict:
    try:
        header, payload, sig = token.split(".")
        return json.loads(_unb64(payload))
    except ValueError as exc:
        raise InvalidToken(str(exc)) from exc
