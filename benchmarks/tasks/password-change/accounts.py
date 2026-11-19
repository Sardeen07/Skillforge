import hashlib
import secrets


class DB:
    def __init__(self):
        self.users = {}      # email -> {"password_hash": str}
        self.sessions = {}   # session id -> email


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()  # out of scope for this change


def login(db, email, password):
    """Return a new session id, or None if the credentials are wrong."""
    user = db.users.get(email)
    if not user or user["password_hash"] != hash_password(password):
        return None
    session_id = secrets.token_urlsafe(24)
    db.sessions[session_id] = email
    return session_id


def current_user(db, session_id):
    return db.sessions.get(session_id)


def change_password(db, session_id, old_password, new_password):
    """Change the logged-in user's password. Returns True on success."""
    raise NotImplementedError
