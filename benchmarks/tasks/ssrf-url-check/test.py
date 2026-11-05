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

def fake(table):
    return lambda host: table[host]


R = fake({"images.example.com": ["93.184.216.34"], "metadata.local": ["169.254.169.254"],
          "intranet.corp": ["10.0.3.7"], "localhost": ["127.0.0.1", "::1"], "v6.internal": ["fd00::1"],
          "mixed.example": ["93.184.216.34", "192.168.1.5"]})


@check("allows-public")
def _():
    f = load("fetcher")
    assert f.is_allowed_url("https://images.example.com/cat.png", R)
    assert f.is_allowed_url("http://images.example.com/cat.png", R)


@check("blocks-internal-hosts")
def _():
    f = load("fetcher")
    for u in ("http://metadata.local/latest", "http://intranet.corp/admin", "http://localhost:8080/",
              "http://v6.internal/", "http://mixed.example/"):
        assert not f.is_allowed_url(u, R), u


@check("blocks-literal-ips")
def _():
    f = load("fetcher")
    for u in ("http://169.254.169.254/latest/meta-data", "http://127.0.0.1/", "http://[::1]/", "http://10.1.2.3/"):
        assert not f.is_allowed_url(u, R), u


@check("blocks-other-schemes")
def _():
    f = load("fetcher")
    for u in ("file:///etc/passwd", "gopher://images.example.com/", "httpx://images.example.com/"):
        assert not f.is_allowed_url(u, R), u


if __name__ == "__main__":
    main()
