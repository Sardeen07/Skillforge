import hashlib
import secrets
import time


class DB:
    def __init__(self):
        self.users = {}          # email -> {"password_hash": str}
        self.reset_tokens = {}   # token -> email


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()  # out of scope for this change


def create_reset_token(db, email, now=None):
    """Return a token to put in the reset link we email, or None if there is no such account."""
    if email not in db.users:
        return None
    token = secrets.token_urlsafe(32)
    db.reset_tokens[token] = email
    return token


def reset_password(db, token, new_password, now=None):
    """Set a new password if the token is valid. Returns True on success."""
    email = db.reset_tokens.get(token)
    if email is None:
        return False
    db.users[email]["password_hash"] = hash_password(new_password)
    return True
