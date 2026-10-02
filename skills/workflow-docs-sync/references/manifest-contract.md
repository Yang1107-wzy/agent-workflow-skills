# Change manifest contract

`scripts/change_manifest.py REPOSITORY --base COMMIT --head COMMIT` accepts the working-tree repository root, not a nested folder or bare repository. Revisions must resolve to single available commit objects; symbolic names, full object IDs, ancestry selectors and annotated commit tags are allowed. Tree/blob objects, ranges, unborn or missing revisions, and revisions beginning with `-` fail with exit 2 and no JSON output. Revisions are resolved once to immutable object IDs before diffing. A non-ancestor base is valid: this is a two-tree comparison, not a merge-base comparison.

Exit 0 emits one schema-version-1 UTF-8 JSON object:

| Field | Meaning |
| --- | --- |
| `base_commit`, `head_commit` | Resolved immutable commit IDs. |
| `commit_changes` | Entries from the comparison of those two commit trees only. Each has `status` and `path`; renames/copies also have `old_path`. Scores such as `R100` are retained. Deleted entries name their former path. Rename detection uses Git's similarity heuristic, so some moves can appear as separate addition/deletion entries. |
| `working_tree.tracked` | Current tracked index/worktree changes, separate from the selected commits, with two-character porcelain status such as ` M`, `M `, `R `, or `UU`. Renames/copies include `old_path`. This state describes the checkout's own index/HEAD, which can differ from the selected head. |
| `working_tree.untracked` | Current untracked files with status `??`; ignored files are excluded. |
| `candidate_documentation_basis` | Always `head_tree_conventions_only`. Suggestions do not prove impact or accuracy. |
| `candidate_documentation_paths` | Files present in the selected head with conventional README, CONTRIBUTING, CHANGELOG, CHANGES or HISTORY filenames (case-insensitive, with optional extension), or under a `docs` directory. Each has `path` and `reason`. Deleted docs, untracked guides and documents under other conventions require separate inspection. |

Git paths are parsed from bytes with NUL delimiters, preserving tabs, newlines and Unicode. Valid UTF-8 names appear unchanged as strings. A non-UTF-8 name appears as `path: null` plus `path_bytes_base64`; a raw rename source uses `old_path: null` plus `old_path_bytes_base64`. Base64 encodes the exact repository-relative bytes. Do not substitute replacement characters or use null as a filename. For raw names, use byte-aware tooling or report the inspection limit. Git tree objects can contain names that the local filesystem cannot represent.

The helper invokes only local Git `rev-parse`, `diff`, `status`, and `ls-tree` reads. It disables optional index updates, filesystem-monitor hooks, untracked-cache updates, external diff and text conversion. Inherited Git directory/index/object-routing environment variables are cleared so the supplied repository is used. Git's global `--no-lazy-fetch` prevents implicit promisor-object fetches; older Git that lacks this option fails with exit 2. Missing objects are not fetched. No output option exists: the caller controls saving stdout and must avoid overwriting prior artifacts.

The commit comparison is stable, but Git reads of the working tree occur separately and are not an atomic snapshot. Concurrent edits can change the reported dirty state. The manifest contains paths/statuses rather than a semantic change summary; inspect code, tests, docs, build configuration and relevant path references to establish actual mismatches.
