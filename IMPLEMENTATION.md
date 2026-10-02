# Implementation plan

- [x] Write fixture-driven tests for file inventory: hashes, duplicates, Unicode paths, ignored packages, symlink exclusion and deterministic ordering.
- [x] Implement a standalone helper in the first skill, test failures, and check copies preserve bytes without overwriting sources/destinations.
- [x] Create and forward-test each skill individually using synthetic workspace artifacts.
- [x] Add a path-scoped installer with preview/apply and collision tests, then skill validation and packaging.
- [x] Document install/invocation in English and Chinese and provide realistic example prompts.
- [x] Run lint, script tests, validator, release ZIP checks and GitHub CI; publish v0.1.0.
- [x] Complete milestone2 one workflow at a time with per-task review and isolated forward evaluation.
- [x] Verify final ten-skill package extraction, dual-target installation and twenty installed helper examples.
- [ ] Verify exact-source cross-platform CI and v0.2.0 publication.
