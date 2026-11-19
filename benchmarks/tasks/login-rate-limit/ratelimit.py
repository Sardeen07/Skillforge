import time


class LoginLimiter:
    """At most `limit` login attempts per client IP address per `window` seconds."""

    def __init__(self, limit=5, window=60):
        self.limit, self.window = limit, window

    def allow(self, environ, now=None):
        """environ is the WSGI environ of a login request. Returns True if it may proceed."""
        raise NotImplementedError
