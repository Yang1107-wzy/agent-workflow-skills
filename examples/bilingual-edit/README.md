# Bilingual editing fixture

All project/person names and observations here are fictional. The 12 ms observation and 8 synthetic samples are illustrative data, not user research or measured workflow improvement.

`zh-to-en/` and `en-to-zh/` contain UTF-8 source prose and completed deliverables: `final-edited.md`, `preservation-map.json`, and `editing-notes.md`. Names use an illustrative translation rather than an asserted official name. The paired examples show both translation directions and retain the prototype stage, limited evidence, and unsubmitted/unapproved application.

From the repository root:

```sh
python skills/workflow-bilingual-edit/scripts/check_preservation.py examples/bilingual-edit/zh-to-en/source.md examples/bilingual-edit/zh-to-en/final-edited.md examples/bilingual-edit/zh-to-en/preservation-map.json
python skills/workflow-bilingual-edit/scripts/check_preservation.py examples/bilingual-edit/en-to-zh/source.md examples/bilingual-edit/en-to-zh/final-edited.md examples/bilingual-edit/en-to-zh/preservation-map.json
```

Both maps pass literal checks. The notes also document semantic review; the checker cannot certify translation or research validity. No-skill baseline editing already preserved the facts competently, so these fixtures demonstrate artifact structure and checks without claiming measured uplift.
