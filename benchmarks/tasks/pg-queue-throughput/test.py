"""Hidden test for the pg-queue-throughput task. Never shown to the agent.

Four defects, chosen because the obvious fix is not the correct one:

  skip-locked        `for update` is already there, so "add a lock" changes nothing;
                     the workers need `for update skip locked` to stop queueing up
  short-transaction  a 2-5s payment call sits inside the claim transaction, holding
                     a row lock for its whole duration
  keyset-pagination  `offset` re-scans every skipped row, so deep pages degrade;
                     passes when a keyset path exists, since task.txt asks for the
                     old behaviour to be kept
  fk-index           Postgres does not index foreign keys automatically, so
                     orders.customer_id has no index and the account page scans

Static checks: they verify the known fix was applied, not measured runtime.
Prints SCORE: n/4 and exits 0 only when all four hold.
"""
import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
WORKER = HERE / "worker.py"


def check_skip_locked(src, _tree, _sql):
    """Row locks without SKIP LOCKED make eight workers behave like one."""
    if re.search(r"for\s+update\s+skip\s+locked", src, re.I | re.S):
        return True, "claims use `for update skip locked`"
    if re.search(r"for\s+update", src, re.I):
        return False, "still plain `for update`, so workers queue behind each other"
    return False, "no row-level locking on the claim at all"


def _executes(node):
    """The literal SQL of a `<conn>.execute("...")` call, lowercased, else None."""
    if not isinstance(node, ast.Call):
        return None
    fn = node.func
    if not (isinstance(fn, ast.Attribute) and fn.attr in ("execute", "executemany")):
        return None
    if not node.args:
        return None
    arg = node.args[0]
    return arg.value.strip().lower() if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None


def _calls_charge(node):
    return any(isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "charge_card"
               for n in ast.walk(node))


def _opens_transaction(stmt):
    """A `with conn.transaction():` block, whatever the connection is called."""
    if not isinstance(stmt, (ast.With, ast.AsyncWith)):
        return False
    for item in stmt.items:
        ctx = item.context_expr
        if isinstance(ctx, ast.Call) and getattr(ctx.func, "attr", None) == "transaction":
            return True
        if getattr(ctx, "attr", None) == "transaction":
            return True
    return False


def check_short_transaction(_src, tree, _sql):
    """The payment call must not run while a transaction is open.

    Walked over each function's top-level statements rather than by regex: the
    original commits early inside an `if row is None:` branch, and a positional
    "is charge_card between a begin and a commit" test would call that a pass.
    """
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        open_tx = False
        for stmt in fn.body:  # top-level only: a nested commit is a different branch
            if _opens_transaction(stmt) and _calls_charge(stmt):
                return False, "payment call is inside a `with conn.transaction():` block"
            if open_tx and _calls_charge(stmt):
                return False, "payment call still runs with the claim transaction open"
            # Only simple statements move the flag. Descending into an `if` or a `try`
            # would let the early-return `commit` on the empty-queue branch look like
            # the transaction had ended on the path the payment call takes.
            if not isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            for node in ast.walk(stmt):
                sql = _executes(node)
                if sql is None:
                    continue
                if sql.startswith(("begin", "start transaction")):
                    open_tx = True
                elif sql.startswith(("commit", "rollback", "end")):
                    open_tx = False
    return True, "payment call runs outside the transaction"


def check_keyset_pagination(src, _tree, _sql):
    """OFFSET scans and discards every skipped row, so deep pages get slower.

    Checks that a keyset path exists, not that `offset` was deleted. task.txt asks to
    keep the same behaviour, so adding a cursor-based function beside the old one is a
    correct fix; an earlier version of this check failed exactly that answer because
    the untouched original still contained the word `offset`.
    """
    cursor = re.search(r"\(\s*created_at\s*,\s*id\s*\)\s*<", src, re.I) or \
        re.search(r"\bwhere\b[^)]*\b(created_at|id)\s*<", src, re.I | re.S)
    if cursor:
        return True, "a keyset cursor path exists for the orders report"
    if re.search(r"\boffset\b", src, re.I):
        return False, "orders report still pages only with `offset`"
    return False, "no keyset cursor comparison for the orders report"


def check_fk_index(_src, _tree, sql):
    """Postgres indexes primary keys, never foreign keys."""
    if re.search(r"create\s+(unique\s+)?index[^;]*\bon\b[^;]*\borders\b[^;]*\(\s*customer_id",
                 sql, re.I | re.S):
        return True, "orders.customer_id is indexed"
    return False, "orders.customer_id is still an unindexed foreign key"


def main():
    if not WORKER.exists():
        print("FAIL  worker.py is missing\nSCORE: 0/4")
        sys.exit(1)
    src = WORKER.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"FAIL  worker.py does not parse: {e}\nSCORE: 0/4")
        sys.exit(1)
    # Any .sql file counts: adding a new migration is the right way to add an index.
    sql = "\n".join(p.read_text(encoding="utf-8") for p in sorted(HERE.rglob("*.sql")))

    checks = [("skip-locked", check_skip_locked),
              ("short-transaction", check_short_transaction),
              ("keyset-pagination", check_keyset_pagination),
              ("fk-index", check_fk_index)]
    passed = 0
    for name, fn in checks:
        ok, why = fn(src, tree, sql)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:<20} {why}")
    print(f"SCORE: {passed}/{len(checks)}")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
