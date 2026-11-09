import hashlib
import hmac
import secrets
import time

TOKEN_TTL = 30 * 60


class DB:
    def __init__(self):
        self.users = {}          # email -> {"password_hash": str}
        self.reset_tokens = {}   # sha256(token) -> {"email": str, "expires": float}


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()  # out of scope for this change


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(db, email, now=None):
    """Return a token to put in the reset link we email, or None if there is no such account.
    Only a hash of the token is stored, so a leaked database cannot be used to reset passwords."""
    if email not in db.users:
        return None
    now = time.time() if now is None else now
    token = secrets.token_urlsafe(32)
    db.reset_tokens[_digest(token)] = {"email": email, "expires": now + TOKEN_TTL}
    return token


def reset_password(db, token, new_password, now=None):
    """Set a new password if the token is valid. Returns True on success. A token works once
    and for 30 minutes; a successful reset revokes every other outstanding token for the user."""
    now = time.time() if now is None else now
    key = _digest(token or "")
    entry = next((v for k, v in db.reset_tokens.items() if hmac.compare_digest(k, key)), None)
    if entry is None or entry["expires"] <= now:
        db.reset_tokens.pop(key, None)
        return False
    email = entry["email"]
    db.users[email]["password_hash"] = hash_password(new_password)
    for k in [k for k, v in db.reset_tokens.items() if v["email"] == email]:
        del db.reset_tokens[k]
    return True
