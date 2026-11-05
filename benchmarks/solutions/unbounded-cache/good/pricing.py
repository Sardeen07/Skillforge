from functools import lru_cache

calls = 0


def _expensive_price(sku, region):
    global calls
    calls += 1
    return (sum(map(ord, sku)) * 7 + len(region)) / 100


@lru_cache(maxsize=10_000)
def price_for(sku, region):
    return _expensive_price(sku, region)
