# Handoff note

Write `handoff.md` with:

- User goal and scope of current work.
- Actual branch/commit and dirty state, linked to `git-snapshot.json`.
- What behavior changed and which files matter.
- Verification table: command; tested source; result/exit code; limitation.
- Unresolved problems and the next command/action.

When checks did not run, write “not run” or “not checked,” not “passed.” Local test success is not remote CI success. Source-tree imports are not evidence that a built wheel installs. A skipped test is not a passing test.

If continuing another person's work, distinguish their existing edits from yours. Preserve pending work and avoid resetting the checkout. Report merge/PR/release status only from current repository or remote evidence.
