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

def _steps(conn, fn):
    count = [0]

    def tick():
        count[0] += 1
        return 0
    conn.set_progress_handler(tick, 100)
    result = fn()
    conn.set_progress_handler(None, 100)
    return result, count[0] * 100


@check("old-api-still-works")
def _():
    f = load("feed"); conn = f.setup(1000)
    assert [r[0] for r in f.list_events(conn, 1, 3)] == [1000, 999, 998]


@check("cursor-pages-cover-everything")
def _():
    f = load("feed"); conn = f.setup(1000)
    seen, cursor = [], None
    for _ in range(100):
        rows, cursor = f.list_events_after(conn, cursor, 70)
        seen += [r[0] for r in rows]
        if cursor is None:
            break
    assert seen == list(range(1000, 0, -1)), (len(seen), seen[:5])


@check("stable-under-inserts")
def _():
    f = load("feed"); conn = f.setup(1000)
    first, cursor = f.list_events_after(conn, None, 50)
    conn.executemany("insert into events (created_at, body) values (?, ?)", [(10**6, "new")] * 20)
    second, _ = f.list_events_after(conn, cursor, 50)
    assert not {r[0] for r in first} & {r[0] for r in second}, "duplicates after new events arrived"
    assert [r[0] for r in second][:1] == [950], second[:1]


@check("deep-pages-cheap", timeout=60)
def _():
    f = load("feed"); conn = f.setup()
    cursor = None
    for _ in range(3):
        _, cursor = f.list_events_after(conn, cursor, 50)
    _, shallow = _steps(conn, lambda: f.list_events_after(conn, cursor, 50))
    cur, walked = None, 0
    while walked < 150000:
        page, cur = f.list_events_after(conn, cur, 5000)
        walked += len(page)
    _, deep = _steps(conn, lambda: f.list_events_after(conn, cur, 50))
    assert deep < max(20 * shallow, 20000), f"deep page cost {deep} VM steps vs {shallow} for a shallow one"


if __name__ == "__main__":
    main()
