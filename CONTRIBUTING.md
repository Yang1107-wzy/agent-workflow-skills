# Contributing

Propose one concrete repeated user task, expected artifacts and a realistic example. Keep skill descriptions narrow enough to avoid overlap. Instructions and resources must preserve user intent and remain self-contained after standalone installation.

Use synthetic fixtures; never commit actual private desktop files, credentials, user inventories or unpublished research. Record discovery evidence with dates and distinguish indexed social posts from fetched primary documentation. Check upstream licenses before reusing any asset.

For helper changes, add meaningful failure regressions and run the script tests. For workflow changes, complete a realistic isolated user request and inspect its actual artifacts. Do not claim better model behavior merely from formatting or metadata checks.

```sh
python -m unittest discover -s tests -v
python scripts/validate_skills.py
ruff check .
ruff format --check .
```

The inventory helper is deliberately bundled in both file skills so each installs independently; keep their bytes identical. Update bilingual README, examples, evaluation notes and changelog when behavior changes.
