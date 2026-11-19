import hashlib
import hmac
import json
import time

SECRET = b"whsec_test_7f3a"
TOLERANCE = 300  # seconds; older signed requests are treated as replays


class InvalidSignature(Exception):
    pass


def verify_webhook(headers, body, secret=SECRET, now=None):
    """Return the parsed event (a dict) if this request genuinely comes from our payment
    provider. headers is a dict; body is the raw request body (bytes).

    The signature covers the timestamp, and requests older than TOLERANCE are rejected,
    so a captured request cannot be replayed later."""
    now = time.time() if now is None else now
    value = {k.lower(): v for k, v in headers.items()}.get("provider-signature", "")
    try:
        parts = dict(item.split("=", 1) for item in value.split(","))
        timestamp, signature = int(parts["t"]), parts["v1"]
    except (KeyError, ValueError):
        raise InvalidSignature("missing or malformed Provider-Signature header")
    expected = hmac.new(secret, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidSignature("signature mismatch")
    if abs(now - timestamp) > TOLERANCE:
        raise InvalidSignature("timestamp outside the tolerance window (possible replay)")
    return json.loads(body)
