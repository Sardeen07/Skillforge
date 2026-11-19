import hashlib
import hmac
import json
import time

SECRET = b"whsec_test_7f3a"


class InvalidSignature(Exception):
    pass


def verify_webhook(headers, body, secret=SECRET, now=None):
    """Return the parsed event (a dict) if this request genuinely comes from our payment
    provider. headers is a dict; body is the raw request body (bytes)."""
    raise NotImplementedError
