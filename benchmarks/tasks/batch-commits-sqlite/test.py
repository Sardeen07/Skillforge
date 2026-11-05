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

import sqlite3, tempfile


def _db():
    path = Path(tempfile.mkdtemp()) / "events.db"
    return path


@check("imports-all-rows")
def _():
    m = load("importer"); path = _db()
    conn = m.open_db(str(path))
    m.import_events(conn, [("click", str(i)) for i in range(500)])
    conn.close()
    assert sqlite3.connect(str(path)).execute("select count(*) from events").fetchone()[0] == 500


@check("few-commits")
def _():
    m = load("importer"); path = _db()
    conn = m.open_db(str(path))
    statements = []
    conn.set_trace_callback(statements.append)
    m.import_events(conn, [("click", str(i)) for i in range(20000)])
    commits = sum(1 for s in statements if s.strip().upper().startswith(("COMMIT", "END")))
    assert commits <= 20, f"{commits} commits for 20,000 rows"


@check("all-or-nothing")
def _():
    m = load("importer"); path = _db()
    conn = m.open_db(str(path))
    rows = [("click", str(i)) for i in range(2500)] + [(None, "bad")]
    try:
        m.import_events(conn, rows)
    except sqlite3.IntegrityError:
        pass
    conn.close()
    n = sqlite3.connect(str(path)).execute("select count(*) from events").fetchone()[0]
    assert n == 0, f"{n} rows left behind by a failed import"


if __name__ == "__main__":
    main()
