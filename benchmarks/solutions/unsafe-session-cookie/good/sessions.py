import base64
import hashlib
import hmac
import json

SECRET = b"rotate-me"


def _sign(body: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(SECRET, body, hashlib.sha256).digest()).decode()


def dump_session(data: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode())
    return body.decode() + "." + _sign(body)


def load_session(cookie: str):
    try:
        body, sig = cookie.rsplit(".", 1)
        if not hmac.compare_digest(_sign(body.encode()), sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(body))
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None
