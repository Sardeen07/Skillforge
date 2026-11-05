from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def invoice_total(lines, tax_rate):
    """lines: [(unit_price_str, quantity)]; tax_rate like "0.0825". Returns the total as "12.34".
    Each line's tax is rounded half-up to the cent before summing, per accounting policy."""
    rate = Decimal(tax_rate)
    total = Decimal("0")
    for price, qty in lines:
        subtotal = Decimal(price) * qty
        tax = (subtotal * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        total += subtotal + tax
    return str(total.quantize(CENT, rounding=ROUND_HALF_UP))
