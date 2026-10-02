# Synthetic documentation synchronization exercise

These files describe a fictional local command-line utility. They contain no user data, live repository or recorded evaluation result. `fixture/base` has the original code and documentation; `fixture/head/tool.py` changes the flag and negative-input contract. The exercise renames the guide without updating its contents, creating documentation work for the skill.

Create disposable commits from the repository's root. Set `exercise_source` to this example directory before entering a temporary directory:

```sh
exercise_source="$(pwd)/examples/docs-sync"
exercise_repo="$(mktemp -d)"
cp -R "$exercise_source/fixture/base/." "$exercise_repo/"
git -C "$exercise_repo" init -b main
git -C "$exercise_repo" config user.name 'Synthetic Fixture'
git -C "$exercise_repo" config user.email fixture@example.invalid
git -C "$exercise_repo" add --all
git -C "$exercise_repo" -c commit.gpgSign=false commit -m 'Synthetic base'
exercise_base="$(git -C "$exercise_repo" rev-parse HEAD)"
cp "$exercise_source/fixture/head/tool.py" "$exercise_repo/tool.py"
git -C "$exercise_repo" mv docs/usage.md docs/cli.md
git -C "$exercise_repo" add --all
git -C "$exercise_repo" -c commit.gpgSign=false commit -m 'Synthetic CLI change and guide rename'
exercise_head="$(git -C "$exercise_repo" rev-parse HEAD)"
```

Run the helper with the real resolved IDs printed by these commits:

```sh
python skills/workflow-docs-sync/scripts/change_manifest.py "$exercise_repo" \
  --base "$exercise_base" --head "$exercise_head"
```

Ask the installed skill to complete a task such as:

> Synchronize this temporary project's documentation from the base commit to the head commit. Update affected authored docs and place docs-sync-plan.md and docs-sync-report.md in a new local report directory. Verify relevant command examples. Do not change the utility source or Git history.

Check the actual edited documents and execution evidence. The changed head accepts `--amount` instead of `--count`; negative amounts now return exit 2 with `amount must be nonnegative`, rather than printing a negative total. References to `docs/usage.md` should point to the renamed guide. The helper should suggest the README and new guide; that alone does not establish that either is accurate. Preserve these original public fixtures when evaluating: work in the temporary copy.

For a scope challenge, make an unrelated untracked note or dirty source change in the disposable repository before invoking the skill. The helper should expose that state separately, and documentation claims must still be grounded in the selected head. This is an exercise, not evidence of efficacy compared with a baseline.
