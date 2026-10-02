"""Install self-contained skills without overwriting existing skill folders."""

import argparse
import json
import shutil
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1] / "skills"


def install(target="codex", scope="user", home=None, project_root=None, selected=(), apply=False):
    base = Path(project_root or Path.cwd()) if scope == "project" else Path(home or Path.home())
    if not base.is_dir():
        raise ValueError("The home or project root must already be a directory.")
    known = {
        p.name: p for p in sorted(BUNDLE.iterdir()) if p.is_dir() and (p / "SKILL.md").is_file()
    }
    names = list(selected) if selected else list(known)
    if not names or len(set(names)) != len(names) or any(name not in known for name in names):
        raise ValueError("Select unique skill names present in this bundle.")
    platforms = ["codex", "claude"] if target == "both" else [target]
    operations = []
    for platform in platforms:
        folder = ".agents" if platform == "codex" else ".claude"
        for name in names:
            source = known[name]
            if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
                raise ValueError("Source skills must not contain symlinks.")
            destination = base / folder / "skills" / name
            if destination.exists() or destination.is_symlink():
                raise ValueError(
                    "An installation destination exists; existing skills are preserved."
                )
            if any(
                destination.resolve().is_relative_to(folder.resolve()) for folder in known.values()
            ):
                raise ValueError("Installation destinations must be outside source skill folders.")
            operations.append((source, destination))
    report = {
        "schema_version": 1,
        "applied": False,
        "destinations": [str(dest) for _, dest in operations],
    }
    if apply:
        created = []
        try:
            for source, destination in operations:
                destination.parent.mkdir(parents=True, exist_ok=True)
                # Reserve the exact directory first, so rollback never owns a raced-in folder.
                destination.mkdir()
                created.append(destination)
                shutil.copytree(
                    source,
                    destination,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
                )
        except BaseException:
            for directory in reversed(created):
                shutil.rmtree(directory)
            raise
        report["applied"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", choices=["codex", "claude", "both"], default="codex")
    p.add_argument("--scope", choices=["user", "project"], default="user")
    p.add_argument("--home", help="User home override for portable testing")
    p.add_argument("--project-root", help="Project destination root; defaults to current directory")
    p.add_argument(
        "--skill", action="append", default=[], help="Install selected skill; repeat as needed"
    )
    p.add_argument(
        "--apply", action="store_true", help="Apply installation; otherwise only preview"
    )
    args = p.parse_args(argv)
    try:
        report = install(
            args.target, args.scope, args.home, args.project_root, args.skill, args.apply
        )
    except (OSError, ValueError) as exc:
        print("install: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
