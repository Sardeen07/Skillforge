def list_orders(store, customer_id):
    """store.orders is a list of {"id": int, "customer_id": int, ...} sorted by id."""
    return [o for o in store.orders if o["customer_id"] == customer_id]
