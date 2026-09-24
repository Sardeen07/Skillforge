#!/usr/bin/env python3
"""Claude Code hook: automatic injection of SkillForge guidance. An experiment, off by default.

SKILLFORGE_HOOK selects the delivery variant under test:
  off      (default) nothing; only the skill is available, and Claude decides when to call it
  brief    rank the raw prompt, sentence by sentence, and inject matching rules
  catalog  inject the one-line-per-rule catalog once per session; Claude fetches rules by ID
  fixed    inject exactly the rules in SKILLFORGE_RULES once per session (expert-selection arm)

Injection only puts text in context; it does not show that the model used it. The
brief is budgeted (SKILLFORGE_HOOK_BUDGET, estimated tokens) under a conservative
character cap: a reported Claude Code behavior cuts long hook output to a preview,
which has not been reproduced here.

Session state (one file per session) keeps apart what was *previously delivered* from
what is *known to be available*. The hook cannot see the context window, so after
compaction or a resumed session it assumes earlier rules may be gone:
  - a follow-up with no new content ("continue", "fix that") while context is intact
    adds nothing; the same follow-up after compaction or resume re-delivers the last
    active rules once;
  - a prompt with new content is ranked on its own; if it matches nothing it is treated
    as a change of task, and the last active rules are dropped, never restored;
  - /clear starts over.
The project stack is detected from the session's working directory unless
SKILLFORGE_STACK is set. Every failure exits 0: a missing brief must never block a prompt.
"""
import hashlib, json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose import LIB, LOG, fetch_command, write_log  # noqa: E402

DEFAULT_BUDGET = 2400   # estimated tokens (chars / 4), about 9,600 characters
SESSIONS = LOG.parent / "sessions"


def session_file(session_id):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:80]
    return SESSIONS / f"{safe}.json" if safe else None


def load(path):
    """{'delivered': [unit keys], 'active_rules': [ids], 'context': 'intact'|'compact'|'resume'}"""
    state = {"delivered": [], "active_rules": [], "context": "intact"}
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        state.update({"delivered": saved} if isinstance(saved, list) else saved)
    except (OSError, ValueError, AttributeError):
        pass
    return state


def save(path, state):
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(path)


def respond(event, text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}))


def project_stack(payload):
    """(stack, versions, source): SKILLFORGE_STACK wins; otherwise the project's manifests."""
    explicit = [s.strip() for s in os.environ.get("SKILLFORGE_STACK", "").split(",") if s.strip()]
    if explicit:
        return explicit, {}, "SKILLFORGE_STACK"
    from retrieval import detect_stack
    stack, versions = detect_stack(payload.get("cwd") or os.getcwd())
    return stack, versions, "detected"


def is_follow_up(prompt):
    """No content of its own to rank: 'continue', 'fix that', 'ok do it'."""
    from retrieval import terms
    return len(set(terms(prompt))) < 2


def session_start(path, source):
    if not path:
        return
    if source == "clear":
        path.unlink(missing_ok=True)
    elif source in ("compact", "resume"):
        # Earlier rules may no longer be in context: nothing counts as delivered, but the
        # last active rules are remembered so a follow-up can get them back.
        state = load(path)
        state.update(delivered=[], context=source)
        save(path, state)


def handle(payload):
    event = payload.get("hook_event_name", "")
    path = session_file(payload.get("session_id"))
    if event == "SessionStart":
        session_start(path, payload.get("source"))
        return
    mode = os.environ.get("SKILLFORGE_HOOK", "off")
    prompt = payload.get("prompt") or ""
    if event != "UserPromptSubmit" or mode not in ("brief", "catalog", "fixed"):
        return
    if not prompt.strip() or prompt.lstrip().startswith("/"):
        return
    from delivery import build_brief, catalog_text
    index = json.loads((LIB / "index.json").read_text(encoding="utf-8"))
    state = load(path) if path else {"delivered": [], "active_rules": [], "context": "intact"}
    emitted = set(state["delivered"])
    budget = int(os.environ.get("SKILLFORGE_HOOK_BUDGET", DEFAULT_BUDGET))

    if mode == "catalog":
        text = catalog_text(index, LIB, "coding", fetch_command())
        key = "catalog:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in emitted or len(text) > budget * 4:
            write_log({"source": "hook", "hook": mode, "result": "catalog skipped",
                       "chars": len(text), "cached": key in emitted})
            return
        respond(event, text)
        save(path, dict(state, delivered=sorted(emitted | {key}), context="intact"))
        write_log({"source": "hook", "hook": mode, "result": "catalog delivered", "chars": len(text)})
        return

    stack, versions, stack_source = project_stack(payload)
    follow_up = is_follow_up(prompt)
    rule_ids, action = None, "ranked"
    if mode == "fixed":
        rule_ids = [r.strip() for r in os.environ.get("SKILLFORGE_RULES", "").split(",") if r.strip()]
        if not rule_ids:
            write_log({"source": "hook", "hook": mode, "error": "SKILLFORGE_RULES is empty"})
            return
        action = "fixed"
    elif follow_up and state["context"] != "intact" and state["active_rules"]:
        rule_ids, action = state["active_rules"], f"restored after {state['context']}"
    brief, keys, log = build_brief(index, LIB, "coding", [prompt], stack, budget, emitted,
                                   os.environ.get("SKILLFORGE_DELIVERY", "rules"), split=True,
                                   abstain_empty=True, rule_ids=rule_ids)
    matched = [u["id"] for u in log["units"][1:] if u["result"] in ("delivered", "session hit")]
    if matched:
        active = matched
    elif follow_up:
        active = state["active_rules"]  # nothing new; the earlier task continues
        action = "follow-up: nothing new" if state["context"] == "intact" else "follow-up: nothing to restore"
    else:
        active, action = [], "new task matched nothing; earlier rules dropped"
    write_log({"source": "hook", "hook": mode, "stack_source": stack_source, "versions": versions,
               "session": {"action": action, "context_before": state["context"],
                           "previously_delivered": state["active_rules"], "active_rules": active}, **log})
    if brief:
        respond(event, brief)
    context = "intact" if brief or state["context"] == "intact" else state["context"]
    save(path, {"delivered": sorted(emitted | keys), "active_rules": active, "context": context})


def main():
    try:
        handle(json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}"))
    except Exception as exc:  # never block the user's prompt
        write_log({"source": "hook", "error": f"{type(exc).__name__}: {exc}"})
    sys.exit(0)


if __name__ == "__main__":
    main()
