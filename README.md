# Practical Agent Workflows

**Reusable workflows for the files, documents and code you actually work with.**

[![CI](https://github.com/Yang1107-wzy/agent-workflow-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Yang1107-wzy/agent-workflow-skills/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Agent Skills](https://img.shields.io/badge/Agent_Skills-Codex_%2B_Claude_Code-blue)

[中文说明](README.zh-CN.md) · [Skill catalog](#skills) · [Examples](examples/prompts.md) · [Research](research/sources-2026-10-02.md) · [Roadmap](ROADMAP.md)

Five focused, original skills with standalone Python helpers, worked prompts and documented outputs. Portable `SKILL.md` instructions support Codex and Claude Code; no model API, paid service or plugin server is required. Helpers use Python 3.10+ standard library; Git is needed for repository snapshots.

## Skills

| Skill | Use it for | Concrete output/helper |
| --- | --- | --- |
| [workflow-materials-intake](skills/workflow-materials-intake/SKILL.md) | Mixed project/research/application materials, duplicates and ambiguous versions | Hash inventory + semantic material index |
| [workflow-desktop-triage](skills/workflow-desktop-triage/SKILL.md) | Desktop, Downloads and scattered file inboxes | Preview plan, classified copies + verified path ledger |
| [workflow-source-writing](skills/workflow-source-writing/SKILL.md) | Technical reports and professional prose from mixed evidence | Complete draft + claim ledger + structural checker |
| [workflow-repo-handoff](skills/workflow-repo-handoff/SKILL.md) | Handing off/resuming code with uncertain branch/test state | Git snapshot + commands/results + next-action note |
| [workflow-skill-research](skills/workflow-skill-research/SKILL.md) | Selecting and maintaining useful Agent workflows | Dated GitHub/X source ledger + explainable ranked shortlist |

These skills have separate triggers. They complement document/rendering and programming tools available in your agent rather than replacing them.

## Install

```sh
git clone https://github.com/Yang1107-wzy/agent-workflow-skills.git
cd agent-workflow-skills
python scripts/validate_skills.py
python scripts/install.py --target both
python scripts/install.py --target both --apply
```

The first installer command previews; `--apply` creates complete copies. Existing skills are never overwritten. Select one skill with `--skill workflow-materials-intake`, or use `--target codex` / `--target claude`.

| Target | User scope | Project scope |
| --- | --- | --- |
| Codex | `~/.agents/skills/<name>` | `<repo>/.agents/skills/<name>` |
| Claude Code | `~/.claude/skills/<name>` | `<repo>/.claude/skills/<name>` |

Project installation:

```sh
python scripts/install.py --scope project --project-root /path/to/repo --target both --apply
```

Paths follow the fetched [Codex skill docs](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skill docs](https://code.claude.com/docs/en/skills). If a new skill does not appear, start a new session or restart the client. Personal Claude skills are local terminal skills; this installer does not upload them to Claude.ai/Cowork or install Claude Code itself. Installation never edits your runtime settings.

You can also download the release ZIP, extract it, and run the same installer from its root.

## Invoke in the agent

**Codex chat:**

```text
Use $workflow-materials-intake to inventory this selected material folder.
Use $workflow-source-writing to draft a project note from these sources.
```

**Claude Code chat:**

```text
/workflow-desktop-triage Classify this Downloads inbox; leave originals in place.
/workflow-repo-handoff Prepare a handoff for this repository without pushing.
```

Descriptions also allow the agent to select skills when a normal request matches. The helper scripts do not call an agent themselves: the agent supplies semantic judgment, source checking and writing.

## Try the helpers without an agent

```sh
python skills/workflow-materials-intake/scripts/inventory.py examples/materials
python skills/workflow-materials-intake/scripts/inventory.py examples/materials --format markdown
python skills/workflow-desktop-triage/scripts/triage.py examples/materials ../classified-demo
python skills/workflow-source-writing/scripts/check_ledger.py examples/evidence-ledger.json --format json
python skills/workflow-skill-research/scripts/rank_candidates.py examples/candidates.json
python skills/workflow-repo-handoff/scripts/snapshot.py .
```

The desktop command previews. Add `--apply` when creating classified copies is the requested action; it creates a new destination outside the source tree, verifies hashes and leaves originals unchanged. Actual moves use the agent's file tools and the skill's path-ledger workflow. The inventory skips hidden entries, symlinks, application packages, code repositories and incomplete downloads; extension categories are only suggestions. Default inventory limit is 1,000 files; hashing large files may take time.

Keep reports outside scanned input folders. Inventories and rejection/review notes can contain personal filenames or excerpts: public examples here are synthetic, and public publication is a separate user decision when you use these skills on your own data.

## Evidence and verification

- Deterministic tests exercise file protection, exact duplicate detection, same-name subfolders, Unicode/legacy consoles, installer collisions, evidence-ledger structure, Git state and source ranking.
- Each workflow is also tested with a realistic isolated agent request; see [EVALUATION.md](EVALUATION.md) for observed outcomes and limits.
- Skill validation checks metadata, self-contained local resources and unfinished instructions; it cannot prove semantic accuracy.
- Evidence checker/ranking metadata is caller-declared. These helpers do not verify truth, visit sources, prove a document is approved or measure objective popularity.
- Runtime-neutral packaging and folder discovery paths are verified. A Claude Code runtime session has not been executed in this evaluation; no identical-model-behavior guarantee is implied.

Research draws on official catalogs and adjacent GitHub workflows, with X as dated discovery evidence. Original instructions/helpers are maintained here; upstream skill bodies are not copied. The [source ledger](research/sources-2026-10-02.md) records dates, access failures and inspiration boundaries.

## Development

```sh
python -m unittest discover -s tests -v
python scripts/validate_skills.py
python -m pip install ruff
ruff check .
ruff format --check .
python scripts/package.py --version 0.1.0
```

CI runs on Linux, Windows and macOS, verifies the bundle, and produces a ZIP. New skills should solve a demonstrated task, have a precise trigger and meaningful example, and preserve portable self-contained resources. See [CONTRIBUTING.md](CONTRIBUTING.md).

The [roadmap](ROADMAP.md) tracks the next professional workflows. A roadmap or skill file does not schedule background work; no recurring automation is configured by this repository.
