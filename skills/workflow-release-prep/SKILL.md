---
name: workflow-release-prep
description: Use when preparing a small package release locally, checking requested version, changelog and selected artifacts, and assembling release notes, a verification checklist and SHA256SUMS. Applies to Python, Node and generic packages; publishing requires separate authorization.
---

# Prepare a small package release

Resolve the package root, requested version, selected existing artifacts and output destination from the request and project conventions. Read the package's release/build/test instructions and changelog. If both `pyproject.toml` and `package.json` exist, inspect both; intentionally different packages need their own specific roots. A tool-only pyproject is generic. Missing or dynamic package versions are unresolved, not generic permission to substitute the requested version.

Resolve `<skill-dir>` to this file's directory and run the read-only helper:

```sh
python "<skill-dir>/scripts/prepare_release.py" /path/to/package \
  --version 1.2.3 --artifact dist/package-file.tar.gz --format json
```

Repeat `--artifact` for each selected file. Python 3.10+ is required; there are no runtime third-party dependencies. Git inspection, when available, requires Git supporting `--no-lazy-fetch`. Read [references/release-contract.md](references/release-contract.md) for the bounded TOML syntax, exit codes and output fields. Exit 0 establishes local metadata/artifact readiness only. Exit 1 retains a useful report of readiness issues; exit 2 means invalid/unsupported input or I/O failure and requires correction before trusting a report.

Verify the actual source selected for release: record its root and Git commit/dirty state, execute the project's relevant existing tests and build commands when feasible, and inspect the resulting artifact's identity and contents. Record commands, exit codes and observed results. A hash cannot prove an artifact came from that source. Preserve user changes; for dirty source report the mismatch or verify an isolated copy of the intended commit without resetting, stashing or silently substituting source. Re-run the helper after any source/build/artifact changes. Do not clear dirty state by creating a commit or adding ignore rules unless authorized.

The helper checks Git only when ROOT is the Git top-level, including worktrees with a `.git` file. An ancestor repository reports `outside_selected_scope` and unverified provenance. For a real monorepo package, inspect its intended containing source repository separately and record that evidence; a generic fixture nested in an unrelated repository does not inherit that commit as provenance.

Complete the requested local assets in a new output directory, preferably outside the source repository so preparation itself does not make it dirty. Create every new file exclusively (`open(..., "x", encoding="utf-8")`) and preserve all existing outputs. Produce:

- `release-notes.md`: version, supported changes from the selected changelog/source, artifact list, source identity and caveats.
- `release-checklist.md`: local preflight result/issues; each actual test/build/check command and result; artifact-to-source evidence; separate unverified remote CI and publication status; concrete remaining blockers.
- `SHA256SUMS`: one `sha256`, two spaces, then the exact artifact path relative to the selected package root per line. Include only successfully hashed selected artifacts; identify any omissions in the checklist. A partial sums file does not mean the release is ready.

Use [references/release-contract.md](references/release-contract.md)'s output recipe and evidence slots when creating these assets. If checks cannot run, finish the local assets with the reason and next action. Deliver their paths, current blockers and actual verification status. Preparation never means uploaded, tagged or published. Publishing requires separate authorization and concrete reviewed assets/checks before that step; this helper performs no publication or network operations.
