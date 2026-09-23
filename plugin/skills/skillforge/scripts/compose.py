#!/usr/bin/env python3
"""Compose a SkillForge brief: the mode's core plus the best module per sub-task.

  compose.py --mode coding --subtask "find why search rerenders" --subtask "fix the bug" --stack react

Selection per sub-task: eligible modules (exported, not rejected, same mode) are ranked by
keyword relevance first, then status (preferred first), benchmark score, and size. At most one
module per overlap group; conflicts are refused; `requires` are loaded too; everything must fit
the budget (core included). Zero modules is a valid answer.

Selection reasons and misses go to a log file (SKILLFORGE_LOG, default ~/.skillforge/compose.log),
not into the brief. Use --session FILE to avoid re-emitting modules already emitted this session;
--reset clears it (use after context compaction). Token numbers are estimates (chars / 4).
"""
import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "library"


def words(text):
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        out.add(w)
        if w.endswith("ies") and len(w) > 4:
            out.add(w[:-3] + "y")
        elif w.endswith("s") and len(w) > 3:
            out.add(w[:-1])
    return out


def relevance(module, need, stack):
    """Keyword matches with the sub-task; the project stack only boosts modules the sub-task already matches."""
    applies = {a.lower() for a in module["applies"]}
    hits = len(applies & need)
    return hits + (1 if hits and applies & stack else 0)


def closure(name, by_name, seen=None):
    """Module plus everything it requires, in load order. None if a requirement is unavailable."""
    seen = seen if seen is not None else []
    if name in seen:
        return seen
    m = by_name.get(name)
    if m is None:
        return None
    for req in m["requires"]:
        if closure(req["target"], by_name, seen) is None:
            return None
    seen.append(name)
    return seen


def compose(index, mode, subtasks, stack=(), budget=None, emitted=()):
    cfg = index["modes"].get(mode)
    if cfg is None:
        raise SystemExit(f"unknown mode {mode!r}; available: {', '.join(index['modes'])}")
    budget = budget or cfg["budget_tokens"]
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
    stack_words = words(" ".join(stack))

    for task in subtasks:
        need = words(task)
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


def render(selected, used, budget, mode, emitted):
    out = [f"# SkillForge brief: {mode} (~{used} of {budget} tokens, estimated)\n"]
    loaded = {m["name"] for m in selected}
    for m in selected:
        key = f"{m['name']}@{m['version']}"
        src = m.get("source") or {}
        origin = f" (from {src['repo']}@{src['commit'][:7]})" if src else ""
        if key in emitted:
            out.append(f"## {m['name']}: already loaded earlier this session (rerun with --reset if context was compacted)\n")
            continue
        out.append(f"## {m['name']}{origin}\n")
        out.append((LIB / m["path"]).read_text().strip() + "\n")
        if m["references"]:
            folder = (LIB / m["path"]).parent
            out.append(f"Reference files for this module (read only if needed): {folder}/\n")
        for ref in m["mentions"]:
            if ref["target"] not in loaded:
                out.append(f"Note: this module mentions `{ref['target']}`, which is not loaded. {ref['reason'] or ''}\n")
    if len(selected) == 1:
        out.append("No additional modules matched these sub-tasks; the core alone applies.\n")
    return "\n".join(out)


def write_log(entry):
    path = Path(os.environ.get("SKILLFORGE_LOG", Path.home() / ".skillforge" / "compose.log"))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}) + "\n")
    except OSError:
        pass  # logging must never break a task


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", default="coding")
    ap.add_argument("--subtask", action="append", default=[], help="repeat once per sub-task")
    ap.add_argument("--stack", default="", help="comma-separated, e.g. react,postgres")
    ap.add_argument("--budget", type=int, help="override the mode's token budget")
    ap.add_argument("--session", help="file tracking modules already emitted this session")
    ap.add_argument("--reset", action="store_true", help="forget what this session already emitted")
    ap.add_argument("task", nargs="?", help="single free-text task (used if no --subtask given)")
    args = ap.parse_args()

    subtasks = args.subtask or ([args.task] if args.task else [])
    index = json.loads((LIB / "index.json").read_text())
    session = Path(args.session) if args.session else None
    emitted = set()
    if session and session.exists() and not args.reset:
        emitted = set(json.loads(session.read_text()))
    stack = [s.strip() for s in args.stack.split(",") if s.strip()]

    selected, used, budget, log = compose(index, args.mode, subtasks, stack, args.budget, emitted)
    print(render(selected, used, budget, args.mode, emitted))
    write_log(log)
    if session:
        session.write_text(json.dumps(sorted(emitted | {f"{m['name']}@{m['version']}" for m in selected})))


if __name__ == "__main__":
    main()
