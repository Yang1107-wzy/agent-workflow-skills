---
name: workflow-skill-research
description: Use when a user wants useful Agent Skill ideas, a GitHub or X workflow survey, or a prioritized plan for building and maintaining a Codex or Claude Code skill library.
---

# Practical skill research

Turn discovery into one implementable workflow, with dated evidence and a clear reason to build it. Use the user's daily tasks and existing skill library as the starting point. Avoid selecting a duplicate simply because it has stars or a popular social post.

Search official product docs for compatibility and GitHub for concrete implementations. Search X when requested or useful for discovering examples; follow referenced projects to primary sources. Record search terms, dates, repository identity and actual source access using [references/source-contract.md](references/source-contract.md). A snippet-only or inaccessible post is an indexed discovery lead, not a fully verified technical source or a live popularity ranking.

Compare a few candidates on utility, portability, evidence, implementation size, maintenance and overlap. For a repeatable shortlist, resolve `<skill-dir>` to this file's directory and use:

```sh
python "<skill-dir>/scripts/rank_candidates.py" candidates.json > ranked.json
```

The rubric is subjective and explicit; the script validates caller-supplied metadata, not actual source access. Star/view snapshots do not establish adoption of a new workflow. Read upstream license terms before reusing code; original implementation with source attribution is often simpler.

Deliver a dated source ledger, an explainable shortlist, and a narrow acceptance specification for the selected workflow: trigger, expected input, useful outputs, helper needs, meaningful test and maintenance cost. If the user requests implementation, build and validate it in the requested repository, then publish within the existing authorization. Keep future candidates in a roadmap, and update shipped status from actual commits/releases/CI.
