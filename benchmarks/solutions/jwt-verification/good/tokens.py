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
        if json.loads(_unb64(header)).get("alg") != "HS256":
            raise InvalidToken("unexpected algorithm")
        expected = hmac.new(SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(sig)):
            raise InvalidToken("bad signature")
        claims = json.loads(_unb64(payload))
    except (ValueError, TypeError) as exc:
        raise InvalidToken(str(exc)) from exc
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] <= time.time():
        raise InvalidToken("expired")
    return claims
