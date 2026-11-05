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

@check("accepts-and-rejects")
def _():
    v = load("validate")
    for ok in ("Ann", "Ann Lee", "dev_42 rocks", "a" * 40):
        assert v.is_valid_display_name(ok), ok
    for bad in ("", " Ann", "Ann ", "Ann  Lee", "Ann!", "a" * 41, "Ann\nLee"):
        assert not v.is_valid_display_name(bad), repr(bad)


@check("no-catastrophic-backtracking", timeout=30)
def _():
    # The regex engine holds the GIL, so a thread timeout cannot interrupt it: run in a subprocess.
    import subprocess
    probe = ("import time, validate\n"
             "t = time.perf_counter()\n"
             "for _ in range(50): assert not validate.is_valid_display_name('a' * 34 + '!')\n"
             "validate.is_valid_display_name(('ab ' * 5000) + '!')\n"
             "print(time.perf_counter() - t)")
    try:
        out = subprocess.run([sys.executable, "-c", probe], cwd=str(HERE), capture_output=True, text=True, timeout=5)
    except subprocess.TimeoutExpired:
        raise AssertionError("validation of a 35-character name ran for more than 5s")
    assert out.returncode == 0, out.stderr[-300:]
    assert float(out.stdout.strip()) < 0.5, f"{out.stdout.strip()}s for 51 checks"


if __name__ == "__main__":
    main()
