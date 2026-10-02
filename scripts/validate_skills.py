"""Validate this bundle's portable skill metadata, local links and helper paths."""

import argparse
import json
import re
import sys
from pathlib import Path


def _metadata(text):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("Missing YAML frontmatter.")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("Unclosed frontmatter.") from None
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if not sep or key in fields:
            raise ValueError("Expected unique plain frontmatter fields.")
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        fields[key] = value
    return fields, "\n".join(lines[end + 1 :])


def validate(root):
    root = Path(root)
    if not root.is_dir():
        raise ValueError("Skills root does not exist.")
    report = {"schema_version": 1, "skills": 0, "issues": []}
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        report["skills"] += 1

        def issue(message, directory=directory):
            report["issues"].append(directory.name + ": " + message)

        file = directory / "SKILL.md"
        if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
            issue("Symlink resources are not self-contained.")
        if not file.is_file():
            issue("Missing SKILL.md.")
            continue
        try:
            metadata, body = _metadata(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issue(str(exc))
            continue
        name = metadata.get("name", "")
        if (
            name != directory.name
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
            or len(name) > 64
        ):
            issue("Name must match the lowercase skill directory.")
        description = metadata.get("description", "")
        if not isinstance(description, str) or not 1 <= len(description) <= 1024:
            issue("Description must be a nonempty string of at most 1024 characters.")
        if not body.strip() or re.search(r"\b(?:TODO|TBD|FIXME)\b", body):
            issue("Workflow is empty or unfinished.")
        targets = re.findall(r"\]\(([^)]+)\)", body) + re.findall(
            r"<skill-dir>/([A-Za-z0-9_./-]+)", body
        )
        for target in targets:
            if target.startswith(("https://", "http://", "#")):
                continue
            target = target.split("#", 1)[0]
            candidate = directory / target
            if (
                not candidate.resolve().is_relative_to(directory.resolve())
                or not candidate.is_file()
            ):
                issue("Missing or escaping local resource: " + target)
        ui = directory / "agents/openai.yaml"
        if ui.exists() and "$" + name not in ui.read_text(encoding="utf-8"):
            issue("Codex default prompt must mention the skill name.")
    if not report["skills"]:
        report["issues"].append("No skills found.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", default=str(Path(__file__).resolve().parents[1] / "skills")
    )
    args = parser.parse_args(argv)
    try:
        report = validate(args.root)
    except (OSError, ValueError) as exc:
        print("validate: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return int(bool(report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
