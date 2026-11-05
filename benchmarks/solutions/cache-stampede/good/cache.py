import threading

_values = {}
_locks = {}
_guard = threading.Lock()


def get_or_compute(key, compute):
    """The cached value for key, computing and storing it on a miss. Concurrent misses for
    one key compute it once (single flight); different keys do not block each other."""
    if key in _values:
        return _values[key]
    with _guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if key not in _values:
            _values[key] = compute()
        return _values[key]


def clear():
    _values.clear()
    _locks.clear()
