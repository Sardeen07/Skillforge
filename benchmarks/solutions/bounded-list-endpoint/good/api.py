DEFAULT_LIMIT, MAX_LIMIT = 50, 100


def list_orders(store, customer_id, limit=None, cursor=None):
    """One page of a customer's orders, oldest first.

    store.orders is a list of {"id": int, "customer_id": int, ...} sorted by id. The cursor is
    the last id of the previous page (opaque to clients), so pages stay stable as orders are added.
    """
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    after = int(cursor) if cursor else 0
    items = []
    for o in store.orders:
        if o["id"] > after and o["customer_id"] == customer_id:
            items.append(o)
            if len(items) == limit + 1:
                break
    more = len(items) > limit
    items = items[:limit]
    return {"items": items, "next_cursor": str(items[-1]["id"]) if more else None}
