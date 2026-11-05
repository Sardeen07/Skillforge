_values = {}


def get_or_compute(key, compute):
    """The cached value for key, computing and storing it on a miss. Called from many threads."""
    if key in _values:
        return _values[key]
    value = compute()
    _values[key] = value
    return value


def clear():
    _values.clear()
