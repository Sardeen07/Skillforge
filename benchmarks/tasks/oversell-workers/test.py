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

import multiprocessing as mp
import sqlite3
import tempfile


def _worker(path, n, q):
    sys.path.insert(0, str(HERE))
    import shop
    try:
        q.put(sum(1 for _ in range(n) if shop.buy(path, "mug")))
    except Exception as exc:  # an error is a failed purchase attempt, reported to the parent
        q.put(f"error: {type(exc).__name__}: {exc}")


@check("single-process", timeout=30)
def _():
    s = load("shop"); path = str(Path(tempfile.mkdtemp()) / "shop.db")
    s.setup(path, 2)
    assert s.buy(path, "mug") and s.buy(path, "mug") and not s.buy(path, "mug")


@check("no-oversell-across-worker-processes", timeout=150)
def _():
    s = load("shop"); path = str(Path(tempfile.mkdtemp()) / "shop.db")
    s.setup(path, 20)
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(path, 10, q)) for _ in range(6)]
    for p in procs: p.start()
    results = [q.get(timeout=120) for _ in procs]
    for p in procs: p.join(10)
    errors = [r for r in results if isinstance(r, str)]
    assert not errors, errors[:2]
    sold = sum(results)
    stock = sqlite3.connect(path).execute("select stock from items").fetchone()[0]
    assert (sold, stock) == (20, 0), f"sold {sold} with 20 in stock; stock now {stock}"


if __name__ == "__main__":
    main()
