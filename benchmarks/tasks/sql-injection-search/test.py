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

@check("finds-products")
def _():
    s = load("store"); conn = s.connect()
    assert s.search_products(conn, "mug") == ["Blue Mug", "Red Mug"], s.search_products(conn, "mug")


@check("injection-blocked")
def _():
    s = load("store"); conn = s.connect()
    got = s.search_products(conn, "' OR '1'='1")
    assert "Secret Prototype" not in got and got == [], got
    got = s.search_products(conn, "x' OR published = 0 --")
    assert got == [], got


@check("apostrophe-works")
def _():
    s = load("store"); conn = s.connect()
    assert s.search_products(conn, "O'Brien") == ["O'Brien's Tea"]


if __name__ == "__main__":
    main()
