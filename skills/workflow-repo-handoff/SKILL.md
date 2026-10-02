---
name: workflow-repo-handoff
description: Use when pausing or handing off coding work, preparing a review summary, or resuming an unfamiliar branch where actual changes, verification results and next steps must be established.
---

# Repository handoff

Leave the next person enough evidence to continue the actual checkout. Read the user's requested scope and repository instructions, then inspect current state. Resolve `<skill-dir>` to this file's directory.

```sh
python "<skill-dir>/scripts/snapshot.py" "<repository-root>" > git-snapshot.json
```

The snapshot records branch, commit and changed paths. It deliberately reports tests, builds and remote CI as unchecked; a clean working tree is not proof of correctness.

Inspect the relevant diff and identify meaningful behavior changes. Discover the project's documented checks before running them; choose checks appropriate to the change and preserve user edits. Record the exact command, interpreter/tool version when relevant, exit code, pass/fail counts and important limitations. Teammate statements, old logs and cached summaries are context, not results for the current source.

Produce the handoff note described in [references/handoff-contract.md](references/handoff-contract.md). Keep tests, build, installed-package smoke checks and remote CI separate. If a check cannot run, explain the concrete reason; do not substitute a weaker check silently.

For an authorized code fix, reproduce the reported failure, make a focused change, run the relevant verification and update the note. Do not commit, push, merge, deploy or discard work just to produce a handoff; perform those actions only when the user requested them or existing authorization covers them.

End with the next concrete action and any unresolved behavior the next person must know. Include enough command evidence to be reproducible without dumping unrelated environment or credentials.
