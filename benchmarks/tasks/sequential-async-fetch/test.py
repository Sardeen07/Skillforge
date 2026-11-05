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

import asyncio


def _fake():
    state = {"now": 0, "max": 0}

    async def fetch(wid):
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        await asyncio.sleep(0.2 - 0.05 * (wid % 3))  # unequal latencies: completion order != input order
        state["now"] -= 1
        return f"widget-{wid}"
    return fetch, state


@check("same-results-in-order")
def _():
    d = load("dashboard"); fetch, _ = _fake()
    assert asyncio.run(d.load_dashboard([3, 1, 2], fetch)) == ["widget-3", "widget-1", "widget-2"]


@check("concurrent")
def _():
    d = load("dashboard"); fetch, _ = _fake()
    start = time.perf_counter()
    asyncio.run(d.load_dashboard(list(range(12)), fetch))
    took = time.perf_counter() - start
    assert took < 1.2, f"12 fetches of 0.15s took {took:.2f}s"


@check("at-most-4-in-flight")
def _():
    d = load("dashboard"); fetch, state = _fake()
    asyncio.run(d.load_dashboard(list(range(12)), fetch))
    assert state["max"] <= 4, f"{state['max']} requests in flight"


if __name__ == "__main__":
    main()
