import time


class Gateway:
    """Stand-in for the card processor."""

    def __init__(self):
        self.charges = []

    def charge(self, customer, amount):
        time.sleep(0.05)
        self.charges.append((customer, amount))
        return {"charge_id": f"ch_{len(self.charges)}", "customer": customer, "amount": amount}


import threading


class IdempotencyConflict(Exception):
    """The key was already used for a different request."""


_results = {}  # in production: a table with a unique constraint on (customer, key)
_locks = {}
_guard = threading.Lock()


def charge(gateway, idempotency_key, customer, amount):
    """POST /charges. Clients send an Idempotency-Key header and retry after timeouts.

    Keys are scoped to the customer (clients generate them, so they can collide across
    customers); a retry returns the stored result; concurrent retries charge once; reusing a
    key for a different request is refused rather than answered with the old result."""
    scope = (id(gateway), customer, idempotency_key)
    request = {"amount": amount}
    with _guard:
        lock = _locks.setdefault(scope, threading.Lock())
    with lock:
        if scope in _results:
            saved_request, result = _results[scope]
            if saved_request != request:
                raise IdempotencyConflict(f"key {idempotency_key!r} was used for a different request")
            return result
        result = gateway.charge(customer, amount)
        _results[scope] = (request, result)
        return result
