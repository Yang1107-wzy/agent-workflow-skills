"""Capture current Git state. Test/build results are deliberately not inferred."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def snapshot(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError("Repository directory does not exist.")

    def run(*args):
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            check=False,
        )
        if result.returncode:
            raise ValueError("Git state cannot be read; select a repository with a commit.")
        return result.stdout

    top = Path(run("rev-parse", "--show-toplevel").strip()).resolve()
    root = root.resolve()
    if top != root:
        raise ValueError("Select the repository root, not a nested folder.")
    branch = run("rev-parse", "--abbrev-ref", "HEAD").strip()
    commit = run("rev-parse", "HEAD").strip()
    entries = run("status", "--porcelain=v1", "-z").split("\0")
    changes = []
    i = 0
    while i < len(entries) and entries[i]:
        entry = entries[i]
        status, path = entry[:2], entry[3:]
        row = {"status": status, "path": path}
        if "R" in status or "C" in status:
            i += 1
            if i >= len(entries) or not entries[i]:
                raise ValueError("Incomplete Git rename status.")
            row["from_path"] = entries[i]
        changes.append(row)
        i += 1
    return {
        "schema_version": 1,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": branch,
        "commit": commit,
        "changes": changes,
        "tests": "not_run_by_snapshot",
        "build": "not_run_by_snapshot",
        "remote_ci": "not_checked_by_snapshot",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repository")
    args = p.parse_args(argv)
    try:
        report = snapshot(args.repository)
    except (OSError, ValueError) as exc:
        print("snapshot: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
