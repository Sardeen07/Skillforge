"""Trap tasks added 2026-11-18: each asks for a feature and leaves out an expert practice
that a library rule states (the pattern that defeated unguided Opus 5.5 on 2026-11-09)."""
T = {}

# ---------------------------------------------------------------- webhook replay
HOOK = '''import hashlib
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
'''
HOOK_FIXED = '''import hashlib
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
'''
T['webhook-verification'] = dict(
    category='security-hard',
    task="Implement verify_webhook in webhooks.py so we only process genuine events from our payment provider. Their docs: every request carries a header `Provider-Signature: t=<unix timestamp>,v1=<signature>`, where the signature is the hex HMAC-SHA256 of `<timestamp>.<raw request body>` keyed with our signing secret. Return the parsed JSON event, and raise InvalidSignature for requests that should not be processed.",
    files={'webhooks.py': HOOK},
    checks='''
import hashlib, hmac, json


def _signed(body, t, secret=b"whsec_test_7f3a"):
    sig = hmac.new(secret, f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return {"Provider-Signature": f"t={t},v1={sig}"}


BODY = json.dumps({"id": "evt_1", "type": "charge.succeeded", "amount": 500}).encode()


def _rejects(w, headers, body, now):
    try:
        w.verify_webhook(headers, body, now=now)
    except w.InvalidSignature:
        return True
    return False


@check("accepts-genuine-event")
def _():
    w = load("webhooks"); now = 1_800_000_000
    assert w.verify_webhook(_signed(BODY, now), BODY, now=now + 5)["id"] == "evt_1"


@check("rejects-tampering-and-wrong-secret")
def _():
    w = load("webhooks"); now = 1_800_000_000
    tampered = BODY.replace(b"500", b"50000")
    assert _rejects(w, _signed(BODY, now), tampered, now), "accepted a modified body"
    assert _rejects(w, _signed(BODY, now, b"other-secret"), BODY, now), "accepted a signature from another secret"
    assert _rejects(w, {}, BODY, now), "accepted a request with no signature header"


@check("rejects-replayed-old-events")
def _():
    w = load("webhooks"); now = 1_800_000_000
    captured = _signed(BODY, now - 3600)
    assert _rejects(w, captured, BODY, now), "a genuine request captured an hour ago was accepted again"
''',
    reference={'webhooks.py': HOOK_FIXED},
    variants=[
        dict(name='no-replay-window', must_fail=['rejects-replayed-old-events'],
             must_pass=['accepts-genuine-event', 'rejects-tampering-and-wrong-secret'],
             why="verifies the signature exactly as documented but accepts old requests forever",
             replace={'webhooks.py': [['    if abs(now - timestamp) > TOLERANCE:\n        raise InvalidSignature("timestamp outside the tolerance window (possible replay)")\n', '']]}),
    ])

# ---------------------------------------------------------------- password change
ACC = '''import hashlib
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
'''
ACC_FIXED = ACC.replace('''def change_password(db, session_id, old_password, new_password):
    """Change the logged-in user's password. Returns True on success."""
    raise NotImplementedError
''', '''def change_password(db, session_id, old_password, new_password):
    """Change the logged-in user's password. Returns True on success.

    Every other session of the user is ended, so anyone who had stolen a session (the
    usual reason people change passwords) is logged out; the current session stays."""
    email = current_user(db, session_id)
    if email is None or db.users[email]["password_hash"] != hash_password(old_password):
        return False
    db.users[email]["password_hash"] = hash_password(new_password)
    for sid in [sid for sid, owner in db.sessions.items() if owner == email and sid != session_id]:
        del db.sessions[sid]
    return True
''')
T['password-change'] = dict(
    category='security-hard',
    task="Add change_password(db, session_id, old_password, new_password) to accounts.py for the account settings page. It must require the user's current password and return True on success, False otherwise.",
    files={'accounts.py': ACC},
    checks='''
def _db(a):
    db = a.DB(); db.users["ann@example.com"] = {"password_hash": a.hash_password("old-pass")}
    return db


@check("requires-current-password")
def _():
    a = load("accounts"); db = _db(a)
    sid = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, sid, "wrong", "new-pass") is False
    assert a.login(db, "ann@example.com", "old-pass"), "password changed without the current password"


@check("changes-the-password")
def _():
    a = load("accounts"); db = _db(a)
    sid = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, sid, "old-pass", "new-pass") is True
    assert a.login(db, "ann@example.com", "new-pass") and not a.login(db, "ann@example.com", "old-pass")


@check("ends-other-sessions")
def _():
    a = load("accounts"); db = _db(a)
    attacker = a.login(db, "ann@example.com", "old-pass")
    mine = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, mine, "old-pass", "new-pass")
    assert a.current_user(db, attacker) is None, "another session (possibly an attacker's) is still logged in after the password change"
''',
    reference={'accounts.py': ACC_FIXED},
    variants=[
        dict(name='no-session-revocation', must_fail=['ends-other-sessions'],
             must_pass=['requires-current-password', 'changes-the-password'],
             why="exactly the requested behavior; leaves every existing session alive",
             replace={'accounts.py': [['    for sid in [sid for sid, owner in db.sessions.items() if owner == email and sid != session_id]:\n        del db.sessions[sid]\n', '']]}),
    ])

# ---------------------------------------------------------------- rate limit behind a proxy
RL = '''import time


class LoginLimiter:
    """At most `limit` login attempts per client IP address per `window` seconds."""

    def __init__(self, limit=5, window=60):
        self.limit, self.window = limit, window

    def allow(self, environ, now=None):
        """environ is the WSGI environ of a login request. Returns True if it may proceed."""
        raise NotImplementedError
'''
RL_FIXED = '''import time
from collections import defaultdict, deque


class LoginLimiter:
    """At most `limit` login attempts per client IP address per `window` seconds."""

    TRUSTED_PROXIES = 1  # our load balancer appends exactly one address to X-Forwarded-For

    def __init__(self, limit=5, window=60):
        self.limit, self.window = limit, window
        self.attempts = defaultdict(deque)

    def client_ip(self, environ):
        """The address our own load balancer saw. Entries left of it are client-supplied
        and can be forged, so only the hop the trusted proxy appended is used."""
        forwarded = [h.strip() for h in environ.get("HTTP_X_FORWARDED_FOR", "").split(",") if h.strip()]
        if len(forwarded) >= self.TRUSTED_PROXIES:
            return forwarded[-self.TRUSTED_PROXIES]
        return environ.get("REMOTE_ADDR", "")

    def allow(self, environ, now=None):
        """environ is the WSGI environ of a login request. Returns True if it may proceed."""
        now = time.time() if now is None else now
        q = self.attempts[self.client_ip(environ)]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
'''
T['login-rate-limit'] = dict(
    category='security-hard',
    task="Implement LoginLimiter.allow in ratelimit.py: at most 5 login attempts per client IP address per minute; return False once a client is over the limit. Our app runs behind one load balancer (an AWS ALB) that adds the client's address to the X-Forwarded-For header, so REMOTE_ADDR is always the load balancer's own address.",
    files={'ratelimit.py': RL},
    checks='''
LB = "10.0.0.2"


def _req(xff):
    return {"REMOTE_ADDR": LB, "HTTP_X_FORWARDED_FOR": xff}


@check("limits-a-client")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    results = [lim.allow(_req("203.0.113.7"), now=1000 + i) for i in range(7)]
    assert results == [True] * 5 + [False] * 2, results


@check("clients-independent-and-window-resets")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    for i in range(5):
        lim.allow(_req("203.0.113.7"), now=1000 + i)
    assert lim.allow(_req("198.51.100.20"), now=1006), "a different client was blocked"
    assert lim.allow(_req("203.0.113.7"), now=1070), "still blocked after the minute passed"


@check("spoofed-header-cannot-bypass")
def _():
    r = load("ratelimit"); lim = r.LoginLimiter()
    # The attacker sends their own X-Forwarded-For; the ALB appends the real address at the end.
    results = [lim.allow(_req(f"1.2.3.{i}, 198.51.100.9"), now=2000 + i) for i in range(8)]
    assert results.count(True) <= 5, f"an attacker rotating a fake X-Forwarded-For got {results.count(True)} attempts in a minute"
''',
    reference={'ratelimit.py': RL_FIXED},
    variants=[
        dict(name='leftmost-forwarded-for', must_fail=['spoofed-header-cannot-bypass'],
             must_pass=['limits-a-client', 'clients-independent-and-window-resets'],
             why="the common choice: the first X-Forwarded-For entry, which the client controls",
             replace={'ratelimit.py': [['            return forwarded[-self.TRUSTED_PROXIES]', '            return forwarded[0]']]}),
    ])

# ---------------------------------------------------------------- JSON error handler
ERR = '''import functools
import logging

logger = logging.getLogger("api")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("invalid request")
        self.errors = errors  # {"field": "message"}


def json_errors(view):
    """Decorator for API views. A view takes a request and returns (status, payload_dict)."""
    return view
'''
ERR_FIXED = '''import functools
import logging
import uuid

logger = logging.getLogger("api")


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("invalid request")
        self.errors = errors  # {"field": "message"}


def json_errors(view):
    """Decorator for API views. A view takes a request and returns (status, payload_dict).

    Expected errors become 400 responses with their field errors. Anything else becomes a
    generic 500 with a request id; the exception and traceback go to the log only, never
    to the client (messages can contain credentials, SQL, hostnames)."""
    @functools.wraps(view)
    def wrapper(request):
        try:
            return view(request)
        except ValidationError as exc:
            return 400, {"error": "validation_failed", "fields": exc.errors}
        except Exception:
            request_id = uuid.uuid4().hex[:12]
            logger.exception("unhandled error in %s (request %s)", view.__name__, request_id)
            return 500, {"error": "internal_error", "request_id": request_id}
    return wrapper
'''
T['json-error-handler'] = dict(
    category='security-hard',
    task="When one of our API views raises, the framework returns an HTML 500 page, which crashes the mobile app's JSON parsing. Make the json_errors decorator in errors.py turn exceptions into JSON responses. Views return (status, payload_dict) and errors should come back the same way; a ValidationError should become a 400 that includes its field errors.",
    files={'errors.py': ERR},
    checks='''
import json, logging


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(); self.records = []

    def emit(self, record):
        self.records.append(record)


@check("passes-through-success")
def _():
    e = load("errors")
    assert e.json_errors(lambda req: (200, {"ok": True}))({}) == (200, {"ok": True})


@check("validation-errors-are-400")
def _():
    e = load("errors")

    def view(req):
        raise e.ValidationError({"email": "is required"})
    status, payload = e.json_errors(view)({})
    assert status == 400 and "email" in json.dumps(payload), (status, payload)


@check("unexpected-errors-are-json-500")
def _():
    e = load("errors")

    def view(req):
        raise RuntimeError("boom")
    status, payload = e.json_errors(view)({})
    assert status == 500 and isinstance(payload, dict) and json.dumps(payload), (status, payload)


@check("does-not-leak-internals")
def _():
    e = load("errors")
    cap = Capture(); lg = logging.getLogger("api"); lg.addHandler(cap); lg.setLevel(logging.DEBUG)

    def view(req):
        raise ConnectionError("could not connect to postgres://billing:hunter2@10.1.2.3:5432/prod")
    try:
        status, payload = e.json_errors(view)({})
    finally:
        lg.removeHandler(cap)
    text = json.dumps(payload)
    for secret in ("hunter2", "10.1.2.3", "postgres://", "Traceback"):
        assert secret not in text, f"the error response exposes {secret!r}: {text}"
    assert any(r.exc_info for r in cap.records), "the unexpected error was not logged with its traceback"
''',
    reference={'errors.py': ERR_FIXED},
    variants=[
        dict(name='echoes-exception-message', must_fail=['does-not-leak-internals'],
             must_pass=['passes-through-success', 'validation-errors-are-400', 'unexpected-errors-are-json-500'],
             why="the obvious handler: returns str(exc) to the client",
             replace={'errors.py': [['            return 500, {"error": "internal_error", "request_id": request_id}',
                                     '            return 500, {"error": "internal_error", "detail": str(__import__("sys").exc_info()[1])}']]}),
    ])

# ---------------------------------------------------------------- unicode usernames
USERS = '''class UsernameTaken(Exception):
    pass


class DB:
    def __init__(self):
        self.users = {}  # key -> username as the person typed it


def register(db, username):
    """Register a username and return it as stored. Raises UsernameTaken if it is in use."""
    username = username.strip()
    if username in db.users:
        raise UsernameTaken(username)
    db.users[username] = username
    return username
'''
USERS_FIXED = '''import unicodedata


class UsernameTaken(Exception):
    pass


class DB:
    def __init__(self):
        self.users = {}  # key -> username as the person typed it


def username_key(username):
    """Comparison key: NFKC folds compatibility forms (fullwidth letters, ligatures) and
    composed/decomposed accents together; casefold handles cases lower() misses (ß, ſ)."""
    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", username).casefold())


def register(db, username):
    """Register a username and return it as stored. Raises UsernameTaken if it is in use."""
    username = unicodedata.normalize("NFC", username.strip())
    key = username_key(username)
    if key in db.users:
        raise UsernameTaken(username)
    db.users[key] = username
    return username
'''
T['unique-usernames'] = dict(
    category='security-hard',
    task="Usernames are supposed to be unique, ignoring case, but someone just registered 'Admin' while 'admin' already exists, and support thinks they are the same account. Fix register() in users.py. Usernames should still be shown the way the person typed them.",
    files={'users.py': USERS},
    checks='''
def _taken(u, db, name):
    try:
        u.register(db, name)
    except u.UsernameTaken:
        return True
    return False


@check("case-insensitive")
def _():
    u = load("users"); db = u.DB()
    assert u.register(db, "admin") == "admin"
    assert _taken(u, db, "Admin") and _taken(u, db, "ADMIN")
    assert u.register(db, "Bob") == "Bob", "display form not preserved"


@check("lookalike-forms-are-the-same-name")
def _():
    u = load("users"); db = u.DB()
    u.register(db, "admin")
    assert _taken(u, db, "\\uff41\\uff44\\uff4d\\uff49\\uff4e"), "fullwidth 'admin' registered as a different user"
    u.register(db, "Jos\\u00e9")
    assert _taken(u, db, "Jose\\u0301"), "'José' with a combining accent registered as a different user"


@check("full-case-folding")
def _():
    u = load("users"); db = u.DB()
    u.register(db, "stra\\u00dfe")
    assert _taken(u, db, "STRASSE"), "'straße' and 'STRASSE' are the same name ignoring case"
''',
    reference={'users.py': USERS_FIXED},
    variants=[
        dict(name='lower-only', must_fail=['lookalike-forms-are-the-same-name', 'full-case-folding'],
             must_pass=['case-insensitive'],
             why="the obvious fix: compare username.lower()",
             replace={'users.py': [['    return unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", username).casefold())', '    return username.lower()'],
                                   ['    username = unicodedata.normalize("NFC", username.strip())', '    username = username.strip()']]}),
    ])
