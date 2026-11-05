class Gateway:
    """Stand-in for the card processor."""

    def __init__(self):
        self.charges = []

    def charge(self, customer, amount):
        import time
        time.sleep(0.05)
        self.charges.append((customer, amount))
        return {"charge_id": f"ch_{len(self.charges)}", "customer": customer, "amount": amount}


def charge(gateway, idempotency_key, customer, amount):
    """Charge the customer and return the processor's result."""
    return gateway.charge(customer, amount)
