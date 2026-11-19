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
    db = a.DB(); db.users["ann@example.com"] = {"password_hash": a.hash_password("old-pass")}
    return db


@check("requires-current-password")
def _():
    a = load("accounts"); db = _db(a)
    sid = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, sid, "wrong", "new-pass") is False
    assert a.login(db, "ann@example.com", "old-pass"), "password changed without the current password"


@check("changes-the-password")
def _():
    a = load("accounts"); db = _db(a)
    sid = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, sid, "old-pass", "new-pass") is True
    assert a.login(db, "ann@example.com", "new-pass") and not a.login(db, "ann@example.com", "old-pass")


@check("ends-other-sessions")
def _():
    a = load("accounts"); db = _db(a)
    attacker = a.login(db, "ann@example.com", "old-pass")
    mine = a.login(db, "ann@example.com", "old-pass")
    assert a.change_password(db, mine, "old-pass", "new-pass")
    assert a.current_user(db, attacker) is None, "another session (possibly an attacker's) is still logged in after the password change"


if __name__ == "__main__":
    main()
