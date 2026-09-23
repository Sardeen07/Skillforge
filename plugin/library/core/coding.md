Coding core (applies to every coding task):
- Read the relevant existing code before changing it, and follow its patterns.
- Before writing new code, check in order: is it needed at all; does the codebase already have it; does the standard library or platform provide it; does an existing dependency cover it. Write new code last, and keep it minimal.
- Keep the change proportional to the request. No speculative abstractions, options, or refactors.
- Never trade away input validation, security, accessibility, data safety, or required behavior to make code shorter.
- Verify before claiming done: run the relevant tests or a direct check and report the actual result. If you could not verify, say so.
- If a fix fails twice, stop guessing and investigate the root cause.
