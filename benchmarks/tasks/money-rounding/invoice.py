def invoice_total(lines, tax_rate):
    """lines: [(unit_price_str, quantity)]; tax_rate like "0.0825". Returns the total as "12.34"."""
    total = 0.0
    for price, qty in lines:
        subtotal = float(price) * qty
        tax = round(subtotal * float(tax_rate), 2)
        total += subtotal + tax
    return f"{total:.2f}"
