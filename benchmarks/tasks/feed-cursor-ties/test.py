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

def _walk(f, conn, limit):
    seen, cursor = [], None
    for _ in range(1000):
        rows, cursor = f.page_after(conn, cursor, limit)
        seen += [r[0] for r in rows]
        if cursor is None:
            break
    return seen


@check("old-api-kept")
def _():
    f = load("feed"); conn = f.setup(50)
    assert len(f.page(conn, 1, 10)) == 10


@check("walks-every-post-once-in-order")
def _():
    f = load("feed"); conn = f.setup(500)
    expected = [r[0] for r in conn.execute("select id from posts order by created_at desc, id desc")]
    for limit in (7, 20, 25):
        seen = _walk(f, conn, limit)
        assert sorted(seen) == sorted(expected) and len(seen) == len(set(seen)), \
            f"limit {limit}: {len(seen)} rows, {len(set(seen))} distinct, {len(expected)} posts"
        order = {pid: i for i, pid in enumerate(expected)}
        assert [order[p] for p in seen] == sorted(order[p] for p in seen), "not newest first"


@check("stable-while-posts-arrive")
def _():
    f = load("feed"); conn = f.setup(200)
    first, cursor = f.page_after(conn, None, 20)
    conn.executemany("insert into posts (created_at, body) values (?, ?)", [(10**6, "new")] * 15)
    second, _ = f.page_after(conn, cursor, 20)
    assert not {r[0] for r in first} & {r[0] for r in second}, "a post appeared on two pages"


if __name__ == "__main__":
    main()
