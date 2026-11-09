import time


class Gateway:
    """Stand-in for the card processor."""

    def __init__(self):
        self.charges = []

    def charge(self, customer, amount):
        time.sleep(0.05)
        self.charges.append((customer, amount))
        return {"charge_id": f"ch_{len(self.charges)}", "customer": customer, "amount": amount}


_results = {}


def charge(gateway, idempotency_key, customer, amount):
    """POST /charges. Clients send an Idempotency-Key header and retry after timeouts."""
    if idempotency_key in _results:
        return _results[idempotency_key]
    result = gateway.charge(customer, amount)
    _results[idempotency_key] = result
    return result
