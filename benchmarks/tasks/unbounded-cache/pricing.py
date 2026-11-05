_cache = {}
calls = 0


def _expensive_price(sku, region):
    global calls
    calls += 1
    return (sum(map(ord, sku)) * 7 + len(region)) / 100


def price_for(sku, region):
    key = (sku, region)
    if key not in _cache:
        _cache[key] = _expensive_price(sku, region)
    return _cache[key]
