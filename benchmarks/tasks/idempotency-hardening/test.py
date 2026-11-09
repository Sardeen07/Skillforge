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


@check("retry-returns-same-charge")
def _():
    p = load("payments"); g = p.Gateway()
    a = p.charge(g, "k-retry", "cus_1", 500)
    b = p.charge(g, "k-retry", "cus_1", 500)
    assert a == b and len(g.charges) == 1, (a, b, g.charges)


@check("concurrent-retries-charge-once")
def _():
    p = load("payments"); g = p.Gateway()
    out = []
    ts = [threading.Thread(target=lambda: out.append(p.charge(g, "k-race", "cus_2", 900))) for _ in range(8)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert len(g.charges) == 1 and all(r == out[0] for r in out), g.charges


@check("keys-scoped-per-customer")
def _():
    p = load("payments"); g = p.Gateway()
    a = p.charge(g, "order-1", "cus_A", 100)
    b = p.charge(g, "order-1", "cus_B", 250)
    assert b["customer"] == "cus_B" and b["amount"] == 250, f"cus_B received {b}"
    assert len(g.charges) == 2


@check("rejects-reused-key-with-different-request")
def _():
    p = load("payments"); g = p.Gateway()
    p.charge(g, "k-reuse", "cus_3", 5)
    try:
        r = p.charge(g, "k-reuse", "cus_3", 500)
    except Exception:
        assert len(g.charges) == 1
        return
    raise AssertionError(f"a $500 request with a key used for $5 returned {r} instead of being refused")


if __name__ == "__main__":
    main()
