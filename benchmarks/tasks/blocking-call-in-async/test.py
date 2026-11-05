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


@check("same-result")
def _():
    s = load("service")
    got = asyncio.run(s.render_report(7))
    assert got == {"order_id": 7, "bytes": len("%PDF-7"), "pdf": "%PDF-7"}, got


@check("event-loop-stays-responsive")
def _():
    s = load("service")

    async def scenario():
        start = time.perf_counter()
        report = asyncio.ensure_future(s.render_report(1))
        await asyncio.sleep(0.05)
        assert await s.health() == "ok"
        latency = time.perf_counter() - start - 0.05
        await report
        return latency

    latency = asyncio.run(scenario())
    assert latency < 0.25, f"health check waited {latency:.2f}s behind a report"


@check("reports-run-concurrently")
def _():
    s = load("service")

    async def three():
        return await asyncio.gather(*(s.render_report(i) for i in range(3)))

    start = time.perf_counter()
    asyncio.run(three())
    took = time.perf_counter() - start
    assert took < 1.4, f"three 0.6s reports took {took:.2f}s"


if __name__ == "__main__":
    main()
