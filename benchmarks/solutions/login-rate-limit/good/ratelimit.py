import time
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
