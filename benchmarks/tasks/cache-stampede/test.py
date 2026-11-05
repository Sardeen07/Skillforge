"""Hidden test. Not shown to the agent. Run after the arm finishes.

Prints PASS/FAIL per check and SCORE: n/m; exits 0 only on a full score. Each check runs
with a time limit, so a hang counts as a failure instead of stalling the run.
"""
GRADER_VERSION = 1
import importlib, os, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CHECKS = []


def check(name, timeout=20):
    def register(fn):
        CHECKS.append((name, fn, timeout))
        return fn
    return register


def load(module):
    """A fresh import of the module the agent edited."""
    sys.modules.pop(module, None)
    return importlib.import_module(module)


def main():
    print("GRADER: behavioral")
    passed = 0
    for name, fn, timeout in CHECKS:
        result = {}

        def run():
            try:
                fn()
                result["ok"] = True
            except BaseException as exc:  # noqa: BLE001 - every failure is a FAIL line
                result["error"] = f"{type(exc).__name__}: {exc}"[:300]

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout)
        if worker.is_alive():
            result["error"] = f"timed out after {timeout}s"
        if result.get("ok"):
            passed += 1
            print(f"PASS {name}")
        else:
            print(f"FAIL {name} {result.get('error')}")
    print(f"SCORE: {passed}/{len(CHECKS)}")
    sys.stdout.flush()
    os._exit(0 if passed == len(CHECKS) else 1)

import threading


def _counter(delay):
    calls = {"n": 0}
    lock = threading.Lock()

    def compute():
        with lock:
            calls["n"] += 1
        time.sleep(delay)
        return "value"
    return compute, calls


@check("returns-values")
def _():
    c = load("cache"); c.clear()
    assert c.get_or_compute("a", lambda: 1) == 1
    assert c.get_or_compute("a", lambda: 2) == 1


@check("single-flight")
def _():
    c = load("cache"); c.clear()
    compute, calls = _counter(0.3)
    results = []
    threads = [threading.Thread(target=lambda: results.append(c.get_or_compute("home", compute))) for _ in range(30)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert results == ["value"] * 30
    assert calls["n"] == 1, f"computed {calls['n']} times for one key"


@check("keys-independent")
def _():
    c = load("cache"); c.clear()
    compute, calls = _counter(0.4)
    start = time.perf_counter()
    threads = [threading.Thread(target=c.get_or_compute, args=(f"k{i}", compute)) for i in range(4)]
    for t in threads: t.start()
    for t in threads: t.join()
    took = time.perf_counter() - start
    assert calls["n"] == 4
    assert took < 1.0, f"four different keys took {took:.2f}s: misses are serialized"


if __name__ == "__main__":
    main()
