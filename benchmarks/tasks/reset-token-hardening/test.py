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

def _db(a):
    db = a.DB(); db.users["ann@example.com"] = {"password_hash": a.hash_password("old")}
    return db


@check("valid-token-resets")
def _():
    a = load("accounts"); db = _db(a)
    t = a.create_reset_token(db, "ann@example.com", now=1000.0)
    assert a.reset_password(db, t, "new", now=1001.0)
    assert db.users["ann@example.com"]["password_hash"] == a.hash_password("new")
    assert a.create_reset_token(db, "nobody@example.com", now=1000.0) is None


@check("expires-after-30-minutes")
def _():
    a = load("accounts"); db = _db(a)
    t = a.create_reset_token(db, "ann@example.com", now=1000.0)
    assert not a.reset_password(db, t, "x", now=1000.0 + 31 * 60), "token still valid after 31 minutes"
    t = a.create_reset_token(db, "ann@example.com", now=5000.0)
    assert a.reset_password(db, t, "y", now=5000.0 + 29 * 60), "token rejected after 29 minutes"


@check("single-use")
def _():
    a = load("accounts"); db = _db(a)
    t = a.create_reset_token(db, "ann@example.com", now=1000.0)
    assert a.reset_password(db, t, "one", now=1001.0)
    assert not a.reset_password(db, t, "two", now=1002.0), "token worked twice"


@check("not-stored-in-plaintext")
def _():
    a = load("accounts"); db = _db(a)
    t = a.create_reset_token(db, "ann@example.com", now=1000.0)
    assert t not in repr(vars(db)), "the reset token is stored as-is: a database leak lets anyone reset passwords"


@check("other-tokens-revoked-after-reset")
def _():
    a = load("accounts"); db = _db(a)
    t1 = a.create_reset_token(db, "ann@example.com", now=1000.0)
    t2 = a.create_reset_token(db, "ann@example.com", now=1010.0)
    assert a.reset_password(db, t2, "new", now=1020.0)
    assert not a.reset_password(db, t1, "attacker", now=1030.0), "an older reset link still works after the password was reset"


if __name__ == "__main__":
    main()
