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

def _taken(u, db, name):
    try:
        u.register(db, name)
    except u.UsernameTaken:
        return True
    return False


@check("case-insensitive")
def _():
    u = load("users"); db = u.DB()
    assert u.register(db, "admin") == "admin"
    assert _taken(u, db, "Admin") and _taken(u, db, "ADMIN")
    assert u.register(db, "Bob") == "Bob", "display form not preserved"


@check("lookalike-forms-are-the-same-name")
def _():
    u = load("users"); db = u.DB()
    u.register(db, "admin")
    assert _taken(u, db, "\uff41\uff44\uff4d\uff49\uff4e"), "fullwidth 'admin' registered as a different user"
    u.register(db, "Jos\u00e9")
    assert _taken(u, db, "Jose\u0301"), "'José' with a combining accent registered as a different user"


@check("full-case-folding")
def _():
    u = load("users"); db = u.DB()
    u.register(db, "stra\u00dfe")
    assert _taken(u, db, "STRASSE"), "'straße' and 'STRASSE' are the same name ignoring case"


if __name__ == "__main__":
    main()
