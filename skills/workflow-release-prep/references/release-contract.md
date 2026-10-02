# Local release preflight contract

`scripts/prepare_release.py ROOT --version VERSION --artifact RELATIVE_PATH` accepts repeated artifacts and `--format json|markdown` (JSON default). It reads existing files and writes UTF-8 stdout only. It never builds, tests, changes inputs/Git, overwrites a file or contacts a remote. Capture output in memory; shell `>` can truncate an existing destination before the helper runs.

| Exit | Meaning |
| --- | --- |
| 0 | Requested version, recognized manifest versions, changelog heading and selected artifacts meet the local checks; an inspected Git tree is clean. |
| 1 | Readiness issues; report remains usable, with `local_ready: false`. |
| 2 | Usage, malformed/unsupported metadata, unavailable root, Git inspection or I/O error; no complete report can be assumed. Closed stdout consumers also exit 2 without a shutdown traceback. |

Versions use exactly `MAJOR.MINOR.PATCH`, ASCII digits and no leading zeroes except `0`. Prerelease/build suffixes are unsupported. Both root manifests are inspected in Python-then-Node order. Mismatch, missing version and dynamic Python version are readiness issues. No manifests, or a pyproject without project metadata, support the explicit generic version; provenance remains unverified.

## Metadata boundaries

Metadata and `CHANGELOG.md` must be nonsymlink ordinary UTF-8 files of at most 1 MiB each. `package.json` must be a JSON object with a literal string version when supplied. Duplicate keys, nonstandard constants, invalid JSON and nesting beyond 64 levels are input errors.

The Python 3.10-compatible TOML extractor is **not a general TOML parser**. Supported package metadata uses bare `[project]` and a single-line `version = "1.2.3"` or `version = '1.2.3'`, optionally followed by a comment. `dynamic` supports a single-line comma-separated array of quoted names, including an empty array or trailing comma. Other values are opaque; this helper does not establish that the entire document is valid TOML. Ordinary dependency arrays may span lines. Bare nested project tables are recognized as package metadata even without a version.

Table names must use bare segments; quoted or escaped table names and quoted assignment keys anywhere are outside this bounded grammar, including Unicode escapes that could spell `project`, `version` or `dynamic`. They are rejected before classifying metadata as generic or matched; ordinary unquoted tool-only pyprojects remain generic. Quoted string values and ordinary multiline dependency arrays remain supported as described above. Duplicate `[project]`, duplicate version/dynamic declarations, inline/dotted project or version forms, nonliteral versions, version/dynamic tables and multiline TOML strings are rejected rather than guessed. Multiline strings anywhere are outside the supported subset because their contents could look like package metadata. For unsupported metadata, inspect it with the project's appropriate TOML tooling and report the unresolved preflight; do not silently claim generic readiness or edit the manifest merely to fit the helper.

`CHANGELOG.md` must have an ATX Markdown section heading containing the exact version token (optional `v` prefix). Headings may have zero to three leading spaces; four-space indented code does not count. Body mentions, fenced code examples and version substrings such as `1.2.30` do not count. This verifies section presence, not changelog quality or completeness.

## Artifacts and Git

Artifacts must be existing, nonempty regular files under ROOT. Absolute paths, `..` traversal, symlink files/ancestors, directories and special files are readiness issues. Newline, carriage-return, NUL and backslash path characters are unsupported. Paths and SHA256 values are reported relative to ROOT; identical selections are deduplicated. SHA256 verifies the bytes inspected, not package structure, installability, build provenance or future unchanged bytes. Run against a stable source/artifact snapshot; the helper is not a filesystem transaction or security boundary against concurrent malicious edits.

On POSIX, an ASCII locale may expose UTF-8 filename bytes as surrogateescaped argument text. Report paths and artifact issues recover those valid UTF-8 bytes into Unicode; undecodable filename bytes are shown as visible `\xNN` escapes without replacement characters. This conversion affects display only: lookup, containment checks and hashing use the original path. Escaped raw-byte names are display evidence, not reusable filesystem paths or `SHA256SUMS` entries.

Git state is checked only when ROOT equals the Git top-level, including worktrees whose `.git` is a file. It describes the **current working tree**, including staged/unstaged/untracked changes across that repository. A dirty selected repository is not locally ready. The commit identifies HEAD, not the origin of the artifact. Ancestor repositories report `outside_selected_scope`; nongit folders and unavailable Git report `not_repository` or `unavailable`. All three unverified cases have `commit: null`, `dirty: null`, and provenance `not_checked`; they may pass the local metadata/artifact checks. Separately inspect a containing monorepo if its source identity matters; no ancestor commit is automatically attributed to a nested package. Missing HEAD in a selected repository is unresolved. Git calls suppress optional index writes and lazy fetch, ignore inherited Git redirection variables, and do not mutate refs or the index.

JSON fields: `schema_version: 1`, `version`, `local_ready`, `readiness_scope`, `manifests`, `changelog`, successfully hashed `artifacts`, `git`, `issues`, `checks_not_run`. Manifest statuses are `generic`, `unresolved`, `matched`, `mismatch`. Artifact rows contain `path`, `bytes`, `sha256`. The helper always lists tests, build, artifact source provenance, remote CI and publication in `checks_not_run`, regardless of any checks the agent independently performed.

## Create reviewable assets without overwriting

Choose a new destination and create it with `exist_ok=False`; use exclusive creation for each UTF-8 file. Never overwrite an earlier release package. For example, with the parsed helper report in `report` and a newly created destination `output`:

```python
from pathlib import Path

output = Path(destination)
output.mkdir(parents=True, exist_ok=False)
with (output / "SHA256SUMS").open("x", encoding="utf-8") as stream:
    for row in report["artifacts"]:
        stream.write(f"{row['sha256']}  {row['path']}\n")
# Write the actual reviewed notes/checklist using the same exclusive mode.
```

The checklist's evidence slots are source root/selected commit/dirty state; metadata and changelog checks; each selected artifact/path/bytes/hash; test command/exit/result; build command/exit/result; artifact-to-source evidence; remote CI evidence or reason unverified; publication state; blockers and next actions. A check not run must have its reason, not a tick inferred from metadata readiness. Record separate helper and agent verification results. If the selected source or artifact changes after checks, repeat relevant checks and replace outputs only through a new destination.
