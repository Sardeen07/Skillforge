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

@check("simple")
def _():
    i = load("invoice")
    assert i.invoice_total([("10.00", 1)], "0.10") == "11.00"


@check("half-up-per-line")
def _():
    i = load("invoice")
    # 1.25 * 0.10 = 0.125 -> 0.13 (half up); float round() gives 0.12
    assert i.invoice_total([("1.25", 1)], "0.10") == "1.38", i.invoice_total([("1.25", 1)], "0.10")
    # values with no exact binary form: 0.35 * 0.5 = 0.175 -> 0.18, 1.15 * 0.5 = 0.575 -> 0.58
    assert i.invoice_total([("0.35", 1)], "0.5") == "0.53", i.invoice_total([("0.35", 1)], "0.5")
    assert i.invoice_total([("1.15", 1)], "0.5") == "1.73", i.invoice_total([("1.15", 1)], "0.5")


@check("no-float-drift")
def _():
    i = load("invoice")
    lines = [("0.10", 1)] * 1000 + [("19.99", 3)]
    # 1000 * 0.10 = 100.00 (+0 tax at 0%), 19.99 * 3 = 59.97
    assert i.invoice_total(lines, "0") == "159.97"
    assert i.invoice_total([("0.1", 3)], "0.0825") == "0.32"  # 0.30 tax 0.02475 -> 0.02


if __name__ == "__main__":
    main()
