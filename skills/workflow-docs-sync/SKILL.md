---
name: workflow-docs-sync
description: Use when synchronizing a project's existing documentation with an explicit Git commit range, including changed CLI examples, behavior, and renamed or deleted paths. Produces an evidence-based plan, completes authorized documentation edits, and reports verification and remaining mismatches.
---

# Synchronize documentation with committed changes

Resolve the repository root, explicit base/head commit revisions, authorized documentation scope and report destination from the request. If a revision or edit scope cannot be inferred, ask for that missing information while inspecting available documentation. Do not silently substitute the working tree for the requested head. A request to synchronize project docs authorizes relevant local documentation edits; do not stop at a manifest or ask again for ordinary edits already in scope.

Resolve `<skill-dir>` to this file's directory. Run the standalone read-only helper:

```sh
python "<skill-dir>/scripts/change_manifest.py" /path/to/repository \
  --base BASE_COMMIT --head HEAD_COMMIT
```

Python 3.10+ and Git supporting the global `--no-lazy-fetch` option are required; there are no runtime third-party dependencies. Exit 0 includes empty diffs. Exit 2 means usage, repository/revision, unsupported Git, unavailable object or I/O failure. The helper writes UTF-8 JSON to stdout and never writes files, changes the index or refs, or contacts remotes. Capture stdout only after exit 0, with exclusive creation of a new manifest file if saving it. See [references/manifest-contract.md](references/manifest-contract.md) for rename fields, raw filenames and scope limits.

Use `commit_changes` to inspect source changes between the resolved commits. The candidate documentation paths are head-tree convention suggestions, not verified impact analysis or an exhaustive document inventory. Inspect existing docs, repository documentation/build conventions, and changed source at the resolved head; search for affected identifiers, CLI flags, examples, behavior descriptions, and references to both old and new renamed paths. Deleted paths may still be mentioned in docs that the helper did not suggest.

Keep `working_tree` changes separate. Preserve pre-existing edits and untracked files. When dirty source or the checked-out commit differs from the requested head, read the selected source using `git show RESOLVED_HEAD:path` and verify commands against an isolated copy of that head. Do not include the dirty behavior in documentation claims, reset/stash/checkout user state, or overwrite a dirty document wholesale. Apply a scoped edit that preserves unrelated changes, or report the concrete overlap if it prevents a correct edit.

Create `docs-sync-plan.md` in a new output directory or unused filename. Record the resolved commits, inspected code/docs evidence, each affected doc and proposed correction, generated-doc handling, and command checks appropriate to the changed behavior. Use exclusive creation for new plan/report artifacts so existing outputs survive. Then implement the authorized affected documentation edits, including renamed/deleted-path references and command examples. Existing docs are intentional edit targets; these edits are separate from the helper's read-only contract.

Respect generated documentation: locate its source and established build command. Edit the source and regenerate only through that convention when authorized and appropriate. If generation cannot run, describe the stale artifact and reason in the report; never manually patch a generated artifact or fabricate successful regeneration. Documentation synchronization does not authorize implementation changes, remote writes, publishing, or new unrelated tools.

Run relevant documented commands against the requested head when feasible, in an isolated temporary workspace if needed. Check expected failure/exit behavior as well as successful examples when a changed contract involves errors. Avoid examples that would send messages, publish, or mutate external services without separate authorization; record those as unverified with the exact reason. Search changed docs for stale flags, old paths and unsupported behavior claims, then inspect the final documentation diff against source evidence.

Create `docs-sync-report.md` with resolved scope and dirty-state caveats; actual files changed; evidence linking each correction to source at head; commands, exit codes and observed results; generated-doc outcomes; and remaining mismatches or unverified examples. State what the helper established separately from what inspection and execution verified. An empty manifest does not prove that documentation was already accurate. Deliver the edited docs and artifacts with concrete limitations; do not infer a quality improvement from a successful helper run.
