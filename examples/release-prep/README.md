# Synthetic release-preparation example

All content is synthetic and contains no private data. The selected artifact is explicitly plain text; it is not a real wheel, built distribution or installable package. There is no test/build/CI/publication evidence in this fixture.

From the repository root:

```sh
python3 skills/workflow-release-prep/scripts/prepare_release.py \
  examples/release-prep/package --version 1.2.3 \
  --artifact artifacts/synthetic-release.txt --format markdown
```

The metadata, heading and artifact hash pass. This nested fixture reports ancestor Git as `outside_selected_scope`, with provenance `not_checked`; the library's ancestor commit is not the fixture's provenance. An unchanged copy of `package/` outside any repository similarly reports unverified provenance. A selected source root that is itself a dirty Git repository causes exit 1. Copying this fixture does not establish build provenance.

Ask an agent to use the skill to prepare notes, checklist and SHA256SUMS in a new output directory for this package. The useful outcome records the synthetic-artifact limitation and unverified tests/build/source provenance/remote CI/publication. Use exclusive output creation and preserve existing files. The helper alone does not create those three deliverables.
