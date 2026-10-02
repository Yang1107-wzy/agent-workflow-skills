---
name: workflow-bilingual-edit
description: Use when polishing or translating professional English or Chinese prose while retaining factual anchors, terminology, hedging, and research, application or deployment status. Supports English-to-Chinese, Chinese-to-English and same-language editing.
---

# Bilingual professional editing

Deliver the actual final edited prose in the requested language and format, `preservation-map.json`, and `editing-notes.md`. Improve clarity, register and flow without upgrading the evidence. Keep inputs unchanged and use unused output filenames or a new directory; never overwrite existing artifacts.

Infer language, audience and tone from the request and source. Proceed with reasonable stylistic choices. If a factual ambiguity affects the meaning, retain the original uncertainty and identify it in the notes. Ask only when essential information cannot be preserved or inferred; ordinary local editing does not require another approval.

Before drafting, identify numbers with units and denominators, names, dates, named methods, recurring terms, hedges and stages. Retain distinctions such as planned/observed/validated, prototype/deployed, preparing/submitted/approved and association/causation in both languages. Use the user's established translations for names and technical terms; document an uncertain translation instead of inventing an official English or Chinese name. Do not add results, credentials or stronger causal claims for polish.

Write complete, usable prose, including every requested section. For requested Word, PDF or LaTeX artifacts, use the available native document tools and verify rendering; this helper neither edits nor renders those formats. Extract UTF-8 plain-text copies of source and edited prose for checking.

Prepare the map using [references/preservation-map.md](references/preservation-map.md). Include relevant factual and terminology anchors, choosing literals specific enough to locate the claim in each language. Map translated literals explicitly; unchanged literals are valid. Record every user-authorized factual change with `factual_change: true` and an explicit `explanation` stating the change and authorization basis. Preserve other facts. The explanation is evidence for review, not independent proof of authorization.

Resolve `<skill-dir>` to this file's directory, then run:

```sh
python "<skill-dir>/scripts/check_preservation.py" source.txt edited.txt preservation-map.json --format json
```

Requires Python 3.10+ and only its standard library. Exit 0 means mapped literals exist with equal occurrence counts; 1 means missing/count findings; 2 means usage, input/schema, JSON or I/O errors. The checker writes only to stdout/stderr. Repair stale anchors, omitted facts or accidental repetition. If deliberate restructuring changes counts, explain the unresolved finding in the notes instead of hiding it by dropping the anchor.

Then review the full source and edited text semantically. Equal counts cannot detect negation, changed units outside an anchor, swapped subjects, omissions outside the map or mistranslation. Check numbers, units, names, dates, hedges, scope and submission/approval/deployment stages regardless of literal pass; consider each authorized change explicitly.

In `editing-notes.md`, record material wording choices, terminology decisions, authorized factual changes, ambiguities, the checker result and remaining findings, and the semantic review outcome. Deliver the final prose and both supporting artifacts with a brief statement of unresolved limits. Publishing, sending or submitting the prose is a separate action requiring applicable authorization.
