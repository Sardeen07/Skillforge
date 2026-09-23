"""Payment gateway client. Third-party HTTP, typically 2-5 seconds per call."""
import urllib.request

GATEWAY = "https://payments.example.com/v1/charge"


def charge_card(order_id, amount):
    """Charge the card on file for an order and return the gateway receipt id."""
    req = urllib.request.Request(
        GATEWAY,
        data=f"order={order_id}&amount={amount}".encode(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode().strip()
