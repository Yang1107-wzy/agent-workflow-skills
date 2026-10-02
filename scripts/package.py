"""Build a deterministic self-contained skill ZIP, excluding local evaluation logs."""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from validate_skills import validate

ROOT = Path(__file__).resolve().parents[1]
DOCS = (
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "DESIGN.md",
    "EVALUATION.md",
)


def package(output, version):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must be MAJOR.MINOR.PATCH.")
    report = validate(ROOT / "skills")
    if report["issues"]:
        raise ValueError("Fix skill validation issues before packaging.")
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Archive already exists; choose a new output path.")
    files = []
    for folder in ("skills", "scripts", "tests", "examples"):
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".pyo")
        )
    files.extend(ROOT / name for name in DOCS)
    files.extend((ROOT / "research").glob("sources-*.md"))
    if any(not p.is_file() or p.is_symlink() for p in files):
        raise ValueError("Bundle inputs must be complete ordinary files.")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output.open("xb") as handle:
            created = True
            with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(files):
                    info = zipfile.ZipInfo(
                        "agent-workflow-skills-"
                        + version
                        + "/"
                        + file.relative_to(ROOT).as_posix(),
                        date_time=(2026, 1, 1, 0, 0, 0),
                    )
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, file.read_bytes())
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    return {
        "archive": str(output),
        "files": len(files),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="0.2.0")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    output = args.output or ROOT / "dist" / ("agent-workflow-skills-" + args.version + ".zip")
    try:
        report = package(output, args.version)
    except (OSError, ValueError) as exc:
        print("package: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
