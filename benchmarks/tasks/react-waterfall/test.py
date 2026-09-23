"""Hidden test for the react-waterfall task. Never shown to the agent.

Checks the three defects the react-performance module covers. Static checks, so
they verify the known fix was applied, not measured runtime. Prints SCORE: n/3
and exits 0 only when all three hold.
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).parent / "page.tsx"


def check_parallel(s):
    """The three independent fetches must not run in series."""
    if "Promise.all" in s or "Promise.allSettled" in s:
        return True, "fetches run in parallel"
    awaits = len(re.findall(r"await\s+get(User|Orders|Recommendations)\s*\(", s))
    return False, f"{awaits} sequential awaits, no Promise.all"


def check_no_barrel(s):
    """Importing from the package root pulls the whole library into the bundle."""
    if re.search(r"""from\s+['"]@/components['"]""", s):
        return False, "still imports from the '@/components' barrel"
    return True, "imports are direct"


def check_hoisted(s):
    """A component declared inside the render body remounts its subtree every render."""
    m = re.search(r"^([ \t]*)(?:function\s+OrderRow|const\s+OrderRow\s*=)", s, re.M)
    if not m:
        return True, "OrderRow removed or inlined into JSX"
    return (len(m.group(1)) == 0), (
        "OrderRow hoisted to module scope" if len(m.group(1)) == 0
        else "OrderRow still declared inside the component"
    )


def main():
    s = SRC.read_text(encoding="utf-8")
    checks = [("parallel-fetches", check_parallel),
              ("no-barrel-import", check_no_barrel),
              ("hoisted-component", check_hoisted)]
    passed = 0
    for name, fn in checks:
        ok, why = fn(s)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:<20} {why}")
    print(f"SCORE: {passed}/{len(checks)}")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
