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

class Store:
    def __init__(self, n):
        self.orders = [{"id": i, "customer_id": 1 if i % 3 else 2} for i in range(1, n + 1)]


@check("default-page-size")
def _():
    a = load("api"); s = Store(1000)
    page = a.list_orders(s, 1)
    assert len(page["items"]) == 50 and page["next_cursor"], (len(page["items"]), page.get("next_cursor"))
    assert [o["id"] for o in page["items"][:3]] == [1, 2, 4]


@check("max-page-size")
def _():
    a = load("api"); s = Store(1000)
    assert len(a.list_orders(s, 1, limit=10_000)["items"]) == 100
    assert len(a.list_orders(s, 1, limit=7)["items"]) == 7


@check("cursor-walks-everything-once")
def _():
    a = load("api"); s = Store(1000)
    seen, cursor = [], None
    for _ in range(100):
        page = a.list_orders(s, 1, limit=100, cursor=cursor)
        seen += [o["id"] for o in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    expected = [o["id"] for o in s.orders if o["customer_id"] == 1]
    assert seen == expected, (len(seen), len(expected))


@check("other-customers-isolated")
def _():
    a = load("api"); s = Store(30)
    page = a.list_orders(s, 2)
    assert all(o["customer_id"] == 2 for o in page["items"]) and page["next_cursor"] is None


if __name__ == "__main__":
    main()
