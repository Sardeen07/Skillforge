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


@check("charges")
def _():
    p = load("payments"); g = p.Gateway()
    r = p.charge(g, "k1", "cus_1", 500)
    assert r["amount"] == 500 and len(g.charges) == 1


@check("retry-returns-original")
def _():
    p = load("payments"); g = p.Gateway()
    first = p.charge(g, "k2", "cus_1", 500)
    again = p.charge(g, "k2", "cus_1", 500)
    assert again == first and len(g.charges) == 1, (again, g.charges)


@check("different-keys-charge-separately")
def _():
    p = load("payments"); g = p.Gateway()
    p.charge(g, "a", "cus_1", 100); p.charge(g, "b", "cus_1", 100)
    assert len(g.charges) == 2


@check("concurrent-retries-charge-once")
def _():
    p = load("payments"); g = p.Gateway()
    results = []
    threads = [threading.Thread(target=lambda: results.append(p.charge(g, "k3", "cus_9", 900))) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(g.charges) == 1, f"{len(g.charges)} charges for one key"
    assert all(r == results[0] for r in results)


if __name__ == "__main__":
    main()
