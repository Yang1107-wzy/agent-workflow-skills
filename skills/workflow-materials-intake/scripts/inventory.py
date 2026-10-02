"""Inventory ordinary files without moving, reading hidden files or following links."""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {"node_modules", "__pycache__", "venv", "dist", "build"}
PACKAGES = (".app", ".photoslibrary", ".bundle", ".framework")
CATEGORIES = {
    "documents": {".pdf", ".docx", ".doc", ".odt", ".rtf"},
    "spreadsheets": {".csv", ".tsv", ".xlsx", ".xls"},
    "presentations": {".pptx", ".ppt", ".odp"},
    "notes": {".md", ".txt"},
    "images": {".png", ".jpg", ".jpeg", ".heic", ".svg", ".webp"},
    "archives": {".zip", ".tar", ".gz", ".7z"},
    "code": {".py", ".js", ".ts", ".swift", ".java", ".kt", ".tex"},
}


def category(path):
    return next(
        (group for group, suffixes in CATEGORIES.items() if path.suffix.lower() in suffixes),
        "review",
    )


def digest(path):
    before = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError("A file changed during inventory; retry with stable files.")
    return h.hexdigest(), after.st_size


def inventory(root, max_files=1000):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Select an existing ordinary directory, not a symlink.")
    if max_files < 1:
        raise ValueError("max-files must be positive.")
    if root.name.lower().endswith(PACKAGES) or (root / ".git").exists():
        raise ValueError(
            "Select ordinary materials, not an application package or repository root."
        )
    root = root.resolve()
    files, skipped = [], []

    def walk_error(error):
        raise error

    for current, directories, filenames in os.walk(root, followlinks=False, onerror=walk_error):
        directory = Path(current)
        retained = []
        for name in sorted(directories):
            p = directory / name
            if (
                p.is_symlink()
                or name.startswith(".")
                or name in SKIP_DIRS
                or name.lower().endswith(PACKAGES)
                or (p / ".git").exists()
            ):
                skipped.append(p.relative_to(root).as_posix())
            else:
                retained.append(name)
        directories[:] = retained
        for name in sorted(filenames):
            p = directory / name
            relative = p.relative_to(root).as_posix()
            if (
                p.is_symlink()
                or name.startswith(".")
                or name.lower().endswith((".part", ".crdownload", ".download"))
                or not p.is_file()
            ):
                skipped.append(relative)
                continue
            if len(files) >= max_files:
                raise ValueError(
                    "File limit exceeded; select a narrower folder or raise --max-files."
                )
            sha, size = digest(p)
            files.append({"path": relative, "size": size, "sha256": sha, "category": category(p)})
    files.sort(key=lambda x: x["path"])
    groups = defaultdict(list)
    for item in files:
        groups[item["sha256"]].append(item["path"])
    duplicates = [
        {"sha256": sha, "paths": paths} for sha, paths in sorted(groups.items()) if len(paths) > 1
    ]
    return {
        "schema_version": 1,
        "root": str(root),
        "files": files,
        "duplicates": duplicates,
        "skipped": sorted(skipped),
    }


def markdown(report):
    def escape(value):
        return (
            str(value)
            .replace("|", "\\|")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    lines = [
        "# Materials inventory",
        "",
        f"Files: {len(report['files'])}; duplicate groups: {len(report['duplicates'])}; skipped entries: {len(report['skipped'])}.",
        "",
        "| Path | Type category | Bytes | SHA256 |",
        "| --- | --- | ---: | --- |",
    ]
    for row in report["files"]:
        lines.append(
            "| " + " | ".join(escape(row[k]) for k in ("path", "category", "size", "sha256")) + " |"
        )
    lines.extend(
        [
            "",
            "Categories describe file types, not document approval or contents. Duplicate groups are byte-identical; no deletion is implied.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root")
    p.add_argument("--max-files", type=int, default=1000)
    p.add_argument("--format", choices=["json", "markdown"], default="json")
    args = p.parse_args(argv)
    try:
        report = inventory(args.root, args.max_files)
    except (OSError, ValueError) as exc:
        print("inventory: " + str(exc), file=sys.stderr)
        return 2
    if args.format == "markdown":
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(
        json.dumps(report, indent=2, ensure_ascii=True)
        if args.format == "json"
        else markdown(report),
        end="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
