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

import gc, tracemalloc


@check("correct-prices")
def _():
    p = load("pricing")
    assert p.price_for("ABC", "eu") == (sum(map(ord, "ABC")) * 7 + 2) / 100


@check("still-caches")
def _():
    p = load("pricing")
    before = p.calls
    for _ in range(100):
        p.price_for("HOT", "us")
    assert p.calls - before == 1, f"computed {p.calls - before} times for one repeated key"


@check("bounded-memory", timeout=60)
def _():
    p = load("pricing")
    for i in range(20000):
        p.price_for(f"warm{i}", "eu")
    gc.collect()
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    for i in range(200000):
        p.price_for(f"sku-{i}-with-a-longish-name", "region-x")
    gc.collect()
    grown = tracemalloc.get_traced_memory()[0] - base
    tracemalloc.stop()
    assert grown < 8_000_000, f"memory grew by {grown / 1e6:.1f} MB over 200k distinct keys"


if __name__ == "__main__":
    main()
