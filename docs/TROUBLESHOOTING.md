# Troubleshooting

**Nothing is injected on my prompts.** The hook is off by default. Set
`SKILLFORGE_HOOK=brief` (or `catalog`) in the environment Claude Code starts from, then run
`/forge-status`. If the last entry says "abstained", retrieval found no rule with enough
evidence: that is intended for vague or unrelated prompts. Name the technology or the symptom.

**`/forge-status` says no brief has been logged.** The hook did not run or could not find
Python. Run the launcher by hand:

```sh
echo '{"hook_event_name":"UserPromptSubmit","session_id":"x","prompt":"postgres workers block each other"}' | SKILLFORGE_HOOK=brief sh plugin/hooks/run-hook.sh
```

No output means no Python 3.9+ was found (`python3`, `python`, `py` are tried). On Windows,
`python3` is often a Microsoft Store alias that prints "Python was not found" and exits 0;
install Python from python.org or use `py -3`.

**Errors.** The hook never fails a prompt; errors go to the log (`SKILLFORGE_LOG`, default
`~/.skillforge/compose.log`) as lines with an `error` field.

**The wrong technology's rules appear.** Set `SKILLFORGE_STACK=postgres,react` (canonical
names from `plugin/library/technologies.json`) to override manifest detection, or name the
technology in the prompt.

**The brief is too long / too short.** `SKILLFORGE_HOOK_BUDGET` sets the estimated-token cap
(default 2400; values outside 200-50,000 fall back to the default). Claude Code is reported
to truncate hook output above 10,000 characters.

**Rules repeat after `/compact`.** By design: after compaction or resume the hook cannot see
what survived, so a follow-up re-delivers the last active rules once.

**`npm test` says no Python 3.9+ found.** `forge/py.mjs` prefers `.venv` in the repository
root, then the PATH. Create a venv: `python3 -m venv .venv`.

**`npm run graders` is slow or skips the Postgres mode.** The `pg-queue-throughput` grader
uses an embedded Postgres from `requirements-dev.txt`; without it, that task is validated in
static mode only. Other graders need only the standard library.

**`validate:library --verify-links` reports 403s.** Some documentation hosts reject
automated requests (dev.mysql.com did). Check those links in a browser.
