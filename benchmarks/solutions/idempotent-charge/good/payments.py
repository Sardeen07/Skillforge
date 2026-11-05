import threading


class Gateway:
    """Stand-in for the card processor."""

    def __init__(self):
        self.charges = []

    def charge(self, customer, amount):
        import time
        time.sleep(0.05)
        self.charges.append((customer, amount))
        return {"charge_id": f"ch_{len(self.charges)}", "customer": customer, "amount": amount}


# In production this is a table with a unique constraint on the key; a dict models it here.
_results = {}
_locks = {}
_guard = threading.Lock()


def charge(gateway, idempotency_key, customer, amount):
    """Charge the customer once per idempotency key and return the processor's result."""
    scope = (id(gateway), idempotency_key)
    with _guard:
        lock = _locks.setdefault(scope, threading.Lock())
    with lock:
        if scope not in _results:
            _results[scope] = gateway.charge(customer, amount)
        return _results[scope]
