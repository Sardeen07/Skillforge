#!/usr/bin/env python3
"""Deliver curated rules for a coding task, as one bounded brief.

  compose.py --subtask "workers block each other in the queue" --stack postgres
  compose.py "free-text prompt; each sentence is ranked on its own"
  compose.py --catalog                  every rule, one line each
  compose.py --rule postgres/lock-skip-locked [--rule ...]
  compose.py --status                   what the most recent brief delivered, and why

Rules are ranked across the whole library (retrieval.py); the brief holds the coding
core plus complete rule text within a budget. Zero rules is a valid answer.

Selection details go to a log (SKILLFORGE_LOG, default ~/.skillforge/compose.log), not
the brief. --session FILE skips rules this conversation already received; --reset
clears it (use after context compaction). Token numbers are estimates (chars / 4).

compose() below is the original keyword module selector, kept only as a scorecard
baseline (score_retrieval.py --baseline). The CLI does not use it.
"""
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

from retrieval import terms

LIB = Path(__file__).resolve().parents[3] / "library"
LOG = Path(os.environ.get("SKILLFORGE_LOG", Path.home() / ".skillforge" / "compose.log"))


def relevance(module, need, stack):
    """Keyword matches with the sub-task; the stack only boosts modules the sub-task already matches."""
    applies = set(terms(" ".join(module["applies"])))
    hits = len(applies & need)
    return hits + (1 if hits and applies & stack else 0)


def closure(name, by_name, seen=None, active=None):
    """Module plus everything it requires, in load order. None if a requirement is unavailable."""
    seen = seen if seen is not None else []
    if name in seen:
        return seen
    active = set() if active is None else active
    if name in active:
        return None
    active.add(name)
    m = by_name.get(name)
    if m is None:
        return None
    for req in m["requires"]:
        if closure(req["target"], by_name, seen, active) is None:
            return None
    active.remove(name)
    seen.append(name)
    return seen


def compose(index, mode, subtasks, stack=(), budget=None, emitted=()):
    """Baseline: one module per sub-task by `applies` keywords, with groups, requires and conflicts."""
    cfg = index["modes"].get(mode)
    if cfg is None:
        raise SystemExit(f"unknown mode {mode!r}; available: {', '.join(index['modes'])}")
    budget = cfg["budget_tokens"] if budget is None else budget
    if budget <= 0:
        raise SystemExit("budget must be positive")
    eligible = [m for m in index["modules"] if m["mode"] == mode and m["status"] in ("provisional", "preferred")]
    by_name = {m["name"]: m for m in eligible}
    log = {"mode": mode, "budget": budget, "subtasks": subtasks, "stack": list(stack), "decisions": [], "misses": []}

    core = by_name.get(cfg["core"])
    if core is None:
        raise SystemExit(f"core module {cfg['core']!r} is missing or not eligible")
    chosen = [core["name"]]
    used = 0 if f"{core['name']}@{core['version']}" in emitted else core["est_tokens"]
    if used > budget:
        raise SystemExit(f"budget {budget} is smaller than the core ({used})")
    groups = {core["overlap_group"]} - {None}
    stack_words = set(terms(" ".join(stack)))

    for task in subtasks:
        need = set(terms(task))
        ranked = sorted((m for m in eligible if m["kind"] == "module"),
                        key=lambda m: (-relevance(m, need, stack_words), m["status"] != "preferred",
                                       -(m["score"] if m["score"] is not None else float("-inf")), m["est_tokens"]))
        picked = None
        for m in ranked:
            rel = relevance(m, need, stack_words)
            if rel == 0:
                break
            if m["name"] in chosen or m["overlap_group"] in groups:
                holder = next((c for c in chosen if by_name[c]["overlap_group"] == m["overlap_group"]), m["name"])
                log["decisions"].append({"subtask": task, "module": m["name"], "result": f"covered by {holder}"})
                picked = holder
                break
            names = closure(m["name"], by_name)
            if names is None:
                log["decisions"].append({"subtask": task, "module": m["name"], "result": "skipped: missing requirement"})
                continue
            new = [n for n in names if n not in chosen]
            all_groups = [by_name[n]["overlap_group"] for n in chosen + new if by_name[n]["overlap_group"] is not None]
            if len(all_groups) != len(set(all_groups)):
                log["decisions"].append({"subtask": task, "module": m["name"], "result": "skipped: dependency overlap"})
                continue
            clash = [(n, c["target"]) for n in new for c in by_name[n]["conflicts"] if c["target"] in chosen + new]
            clash += [(c, n) for c in chosen for n in new if n in {x["target"] for x in by_name[c]["conflicts"]}]
            if clash:
                log["decisions"].append({"subtask": task, "module": m["name"], "result": f"skipped: conflicts {clash}"})
                continue
            cost = sum(by_name[n]["est_tokens"] for n in new if f"{n}@{by_name[n]['version']}" not in emitted)
            if used + cost > budget:
                log["decisions"].append({"subtask": task, "module": m["name"],
                                         "result": f"skipped: over budget ({used}+{cost}>{budget})"})
                continue
            chosen += new
            used += cost
            groups |= {by_name[n]["overlap_group"] for n in new} - {None}
            log["decisions"].append({"subtask": task, "module": m["name"], "result": f"selected (relevance {rel})",
                                     "added": new})
            picked = m["name"]
            break
        if picked is None:
            log["misses"].append(task)
    return [by_name[n] for n in chosen], used, budget, log


def write_log(entry):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}) + "\n")
    except OSError:
        pass  # logging must never break a task


def status():
    """Human-readable summary of the most recent brief in the log."""
    try:
        entries = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
        last = [e for e in entries if "units" in e][-1]
    except (OSError, IndexError, json.JSONDecodeError):
        return f"No SkillForge brief has been logged yet ({LOG})."
    lines = [f"Last brief: {last.get('at')} via {last.get('source', 'cli')}, "
             f"~{last.get('estimated_output_tokens')} of {last.get('budget')} estimated tokens."]
    for part in last.get("parts", []):
        found = ", ".join(f"{r['id']} ({r['score']})" for r in part["rules"]) or "nothing relevant (abstained)"
        lines.append(f"- \"{part['text'][:80]}\" -> {found}")
    for u in last.get("units", []):
        why = f" (required by {u['required_by']})" if u.get("required_by") else ""
        lines.append(f"  {u['result']:18} {u['id']}{why}")
    session = last.get("session")
    if session:
        lines.append(f"Session: {session['action']}. Context before this prompt: {session['context_before']}.")
        lines.append(f"  previously delivered: {', '.join(session['previously_delivered']) or 'none'}")
        lines.append(f"  active now: {', '.join(session['active_rules']) or 'none'}")
        lines.append("  (Delivered is not the same as still in context: after compaction or resume the "
                     "hook cannot see what survived.)")
    return "\n".join(lines)


def fetch_command():
    return f'"{sys.executable}" "{Path(__file__).resolve()}"'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delivery", choices=("modules", "rules"), default=os.environ.get("SKILLFORGE_DELIVERY", "rules"),
                    help="rules inlines matching complete rules; modules delivers full modules (ablation)")
    ap.add_argument("--explain", help="write selection and exact estimated output size as JSON")
    ap.add_argument("--mode", default="coding")
    ap.add_argument("--subtask", action="append", default=[], help="repeat once per sub-task")
    ap.add_argument("--stack", default=os.environ.get("SKILLFORGE_STACK", ""), help="comma-separated, e.g. react,postgres")
    ap.add_argument("--budget", type=int, help="override the mode's token budget")
    ap.add_argument("--session", help="file tracking rules already delivered in this conversation")
    ap.add_argument("--reset", action="store_true", help="forget what this session already received")
    ap.add_argument("--catalog", action="store_true", help="print every rule, one line each")
    ap.add_argument("--rule", action="append", default=[], help="print a rule's full text by ID; repeatable")
    ap.add_argument("--status", action="store_true", help="summarize the most recent brief")
    ap.add_argument("task", nargs="?", help="free text (used if no --subtask); split into sentences")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.status:
        print(status())
        return

    from delivery import build_brief, catalog_text, get_rules
    index = json.loads((LIB / "index.json").read_text(encoding="utf-8"))
    if args.catalog:
        print(catalog_text(index, LIB, args.mode, fetch_command()), end="")
        return
    if args.rule:
        text, missing = get_rules(index, LIB, args.mode, args.rule)
        print(text, end="")
        if missing:
            sys.exit(f"unknown rule ID(s): {', '.join(missing)}. Run with --catalog for the list.")
        write_log({"source": "rule", "rules": args.rule})
        return

    session = Path(args.session) if args.session else None
    emitted = set()
    if session and session.exists() and not args.reset:
        emitted = set(json.loads(session.read_text(encoding="utf-8")))
    stack = [s.strip() for s in args.stack.split(",") if s.strip()]
    subtasks = args.subtask or ([args.task] if args.task else [])
    brief, keys, log = build_brief(index, LIB, args.mode, subtasks, stack, args.budget, emitted,
                                   args.delivery, split=not args.subtask)
    print(brief, end="")
    write_log({"source": "cli", **log})
    if args.explain:
        Path(args.explain).write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    if session:
        session.parent.mkdir(parents=True, exist_ok=True)
        temporary = session.with_name(session.name + f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps(sorted(emitted | keys)), encoding="utf-8")
        temporary.replace(session)


if __name__ == "__main__":
    main()
