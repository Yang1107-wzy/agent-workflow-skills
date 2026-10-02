# Workflow library design

Ten focused Agent Skills in skills/workflow-*/SKILL.md, using only portable name/description frontmatter plus optional Codex agents/openai.yaml metadata. Common runtime-neutral Python helpers for inventory, classified copies, source-ledger validation and bundle installation. Skills route to bundled scripts by their own location, without hardcoded user paths or product-only tool names.

Python >=3.10; standard-library runtime; no model API calls. Public examples are synthetic. File operations are scoped to user-selected roots; inventory and plans are read-only, and classified copying creates a new output directory without deleting originals. Actual desktop moves are separate agent operations governed by the user's scope and use a path ledger. Do not operate on this user's real desktop during development.

Installer supports --target codex|claude|both and --scope user|project, previews by default, refuses existing skill destinations and installs complete self-contained skill folders on --apply. No settings rewrites, runtime installation or replacement of existing skills.

Validation checks skill metadata, package-local links and executable scenarios; CI tests scripts on Linux/Windows/macOS. Behavioral skill evaluations are reported separately from deterministic script tests. No claim of having tested the Claude runtime unless actually run.

Professional expansion adds source-evidenced action extraction, coverage-aware numerical reports, explicit-commit documentation manifests, local release preparation and bilingual factual editing. Helpers validate bounded structure and observable invariants; agent judgment completes semantic extraction/writing/edits. Numerical report approximations expose exact rational metadata. Git/local release checks never imply external publication. Full workflow validation uses synthetic isolated projects and outputs, followed by package extraction/dual-target installation checks.
