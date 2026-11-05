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

def _data(n):
    rows = [{"email": f"user{i}@example.com"} for i in range(n)]
    rows += [{"email": "USER5@example.com"}, {"email": "user3@example.com"}, {"email": "user5@EXAMPLE.com"}]
    return rows


@check("same-output")
def _():
    d = load("dedupe")
    assert d.find_duplicate_emails(_data(10)) == ["user5@example.com", "user3@example.com"]
    assert d.find_duplicate_emails([]) == []


@check("fast-on-60k", timeout=30)
def _():
    d = load("dedupe")
    rows = _data(60000)
    start = time.perf_counter()
    got = d.find_duplicate_emails(rows)
    took = time.perf_counter() - start
    assert got == ["user5@example.com", "user3@example.com"], got
    assert took < 1.5, f"took {took:.2f}s for 60k rows"


if __name__ == "__main__":
    main()
