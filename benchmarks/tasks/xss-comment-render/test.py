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

@check("normal-markup")
def _():
    r = load("render")
    html = r.render_comment("Ann", "Nice post", "https://ann.example")
    assert html == '<div class="comment"><a href="https://ann.example" title="Ann">Ann</a><p>Nice post</p></div>', html


@check("escapes-body")
def _():
    r = load("render")
    html = r.render_comment("Ann", "<script>alert(1)</script> & co", "https://ann.example")
    assert "<script>" not in html and "&lt;script&gt;" in html and "&amp; co" in html, html


@check("escapes-attributes")
def _():
    r = load("render")
    html = r.render_comment('x" onmouseover="alert(1)', "hi", "https://ann.example")
    assert 'onmouseover="alert' not in html, html


@check("rejects-javascript-urls")
def _():
    r = load("render")
    html = r.render_comment("Ann", "hi", "javascript:alert(document.cookie)")
    assert "javascript:" not in html.lower(), html


if __name__ == "__main__":
    main()
