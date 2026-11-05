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

@check("same-output")
def _():
    r = load("report")
    got = r.customer_totals(r.setup(5, 2))
    assert got == [("Customer 0001", 201), ("Customer 0002", 401), ("Customer 0003", 601),
                   ("Customer 0004", 801), ("Customer 0005", 1001), ("No Orders Ltd", 0)], got


@check("constant-query-count")
def _():
    r = load("report")
    for n in (10, 400):
        conn = r.setup(n, 2)
        statements = []
        conn.set_trace_callback(statements.append)
        rows = r.customer_totals(conn)
        assert len(rows) == n + 1
        assert len(statements) <= 2, f"{len(statements)} statements for {n} customers"


if __name__ == "__main__":
    main()
