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


@check("single-thread-behavior")
def _():
    w = load("wallet")
    acct = w.Wallet(100)
    assert acct.withdraw(30) == 70
    try:
        acct.withdraw(80)
    except w.InsufficientFunds:
        pass
    else:
        raise AssertionError("overdraft allowed")
    assert acct.balance == 70


@check("never-negative-under-concurrency")
def _():
    w = load("wallet")
    for _ in range(5):
        acct = w.Wallet(100)
        ok = []

        def attempt():
            try:
                acct.withdraw(10)
                ok.append(1)
            except w.InsufficientFunds:
                pass
        threads = [threading.Thread(target=attempt) for _ in range(40)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert acct.balance >= 0, f"balance {acct.balance}"
        assert len(ok) == 10 and acct.balance == 0, (len(ok), acct.balance)


if __name__ == "__main__":
    main()
