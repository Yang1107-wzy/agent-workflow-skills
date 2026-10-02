---
name: workflow-desktop-triage
description: Use when a user wants to tidy a desktop, Downloads folder or file inbox, preview a classification plan, or create an organized workspace from scattered ordinary files.
---

# Desktop triage

Make the selected inbox understandable and usable. Use the user's existing folder system when supplied; otherwise propose a compact structure with a review bucket. Resolve `<skill-dir>` to this file's directory.

For a read-only inventory and classification preview:

```sh
python "<skill-dir>/scripts/triage.py" "<selected-inbox>" "<new-classified-folder>" > triage-plan.json
```

For authorized classified **copies**, run the same command with `--apply`. The destination must be new and outside the source tree. The helper copies ordinary files into type groups while preserving subpaths, checks hashes, and saves `copy-ledger.json`. It leaves originals in place; do not report that the desktop was cleared. Categories are extension-based suggestions, not semantic conclusions.

Skip hidden configuration, symlinks, application/photo-library packages, code repositories and active download files. Inspect ambiguous documents before assigning project/topic categories. Byte-identical files are candidates for review, not disposable merely because they duplicate another path.

If the user specifically requests moving originals, use the agent's available file tools within that authorized folder, following [references/move-ledger.md](references/move-ledger.md). A preview request authorizes only a preview. A move request does not authorize deletion or emptying trash.

Deliver a short category summary, the path ledger and the actual remaining review items. Verify destination files and preserve working links. Distinguish completed copies, completed moves and proposed actions in the report.
