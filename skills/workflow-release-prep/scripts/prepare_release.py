#!/usr/bin/env python3
"""Read-only local release preflight; Python 3.10+, standard library only."""

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

MAX_METADATA_BYTES = 1024 * 1024
SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", re.ASCII)
LITERAL = r"""(?:"([^"\\\r\n]*)"|'([^'\r\n]*)')"""
NOT_RUN = ["tests", "build", "artifact_source_provenance", "remote_ci", "publication"]


def version_string(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError("version must be literal MAJOR.MINOR.PATCH; no prerelease/build suffix")
    return value


def read_text(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"metadata must be an ordinary nonsymlink file: {path.name}")
    with path.open("rb") as stream:
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError(f"metadata exceeds 1 MiB: {path.name}")
    return raw.decode("utf-8")


def python_version(text):
    """Extract only bounded, single-line literal project version/dynamic assignments.

    This is deliberately not a TOML parser: unrelated values are opaque. Unsupported
    spellings of package metadata are errors, never silently generic metadata.
    """
    section = None
    project_seen = False
    table_seen = False
    found = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if '"""' in line or "'''" in line:
            raise ValueError("multiline TOML strings are outside this literal extractor")
        if line.startswith("["):
            # Never decode quoted/escaped table names or silently treat them as generic.
            if re.match(r"""\[+[^\]#]*["'\\]""", line):
                raise ValueError("quoted/escaped TOML table names are unsupported")
            # Quoted/spaced spellings of project are ambiguous to this extractor.
            if re.match(r"""\[+\s*["']?project\b""", line) and not re.match(
                r"\[(?:project|project\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\]\s*(?:#.*)?$", line
            ):
                raise ValueError("unsupported project table syntax in pyproject.toml")
            match = re.fullmatch(r"\[([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\]\s*(?:#.*)?", line)
            section = match.group(1) if match else "other"
            if section.startswith("project."):
                project_seen = True
                if section.split(".")[1] in ("version", "dynamic"):
                    raise ValueError("project version/dynamic tables are unsupported")
            if section == "project":
                if table_seen:
                    raise ValueError("duplicate [project] table")
                project_seen = True
                table_seen = True
            continue
        # Check before section filtering: an escaped root key can also hide project metadata.
        if re.match(r"""(?:"(?:\\.|[^"\\])*"|'[^']*')\s*(?:=|\.)""", line):
            raise ValueError("quoted TOML keys are outside this literal extractor")
        if section is None and re.match(r"""["']?project\b""", line):
            raise ValueError("inline/dotted project metadata is unsupported")
        if section != "project":
            continue
        # Only bare keys are supported for the metadata we extract.
        if re.match(r"""["'](?:version|dynamic)["']""", line):
            raise ValueError("quoted project version/dynamic keys are unsupported")
        assignment = re.match(r"(version|dynamic)\b(.*)$", line)
        if not assignment:
            continue
        key, tail = assignment.groups()
        if key in found:
            raise ValueError(f"duplicate project.{key}")
        if key == "version":
            literal = re.fullmatch(r"\s*=\s*" + LITERAL + r"\s*(?:#.*)?", tail)
            if not literal:
                raise ValueError("project.version requires one single-line quoted literal")
            found[key] = version_string(
                next(value for value in literal.groups() if value is not None)
            )
        else:
            array = re.fullmatch(r"\s*=\s*\[(.*)\]\s*(?:#.*)?", tail)
            if not array:
                raise ValueError("project.dynamic requires a single-line array of quoted names")
            body = array.group(1).strip()
            names = []
            while body:
                item = re.match(LITERAL, body)
                if not item:
                    raise ValueError("project.dynamic contains unsupported values")
                names.append(next(value for value in item.groups() if value is not None))
                body = body[item.end() :].strip()
                if body:
                    if not body.startswith(","):
                        raise ValueError("project.dynamic names require commas")
                    body = body[1:].strip()
            if len(names) != len(set(names)):
                raise ValueError("duplicate project.dynamic name")
            found[key] = names
    if not project_seen:
        return "generic", None
    if "version" not in found or "version" in found.get("dynamic", []):
        return "unresolved", found.get("version")
    return "literal", found["version"]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"nonstandard JSON constant: {value}")


def bounded_json(text):
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 64:
                raise ValueError("package.json nesting exceeds 64 levels")
        elif char in "]}":
            depth -= 1
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def manifests(root, requested, issues):
    rows = []
    for name, kind in (("pyproject.toml", "python"), ("package.json", "node")):
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        text = read_text(path)
        if kind == "python":
            status, version = python_version(text)
        else:
            data = bounded_json(text)
            if not isinstance(data, dict):
                raise ValueError("package.json must be an object")
            status = "unresolved" if "version" not in data else "literal"
            version = version_string(data["version"]) if status == "literal" else None
        if status == "literal":
            status = "matched" if version == requested else "mismatch"
        rows.append({"path": name, "kind": kind, "version": version, "status": status})
        if status in ("unresolved", "mismatch"):
            issues.append(f"{name}: {status} version (requested {requested})")
    return rows


def artifact(root, relative, issues):
    path = Path(relative)
    if (
        not relative
        or path.is_absolute()
        or ".." in path.parts
        or any(char in relative for char in ("\n", "\r", "\x00", "\\"))
    ):
        issues.append(f"artifact path must be contained and relative: {relative!r}")
        return None
    candidate = root
    for part in path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            issues.append(f"symlink artifact or ancestor: {relative}")
            return None
    try:
        metadata = candidate.stat()
    except FileNotFoundError:
        issues.append(f"missing artifact: {relative}")
        return None
    if not candidate.resolve().is_relative_to(root) or not stat.S_ISREG(metadata.st_mode):
        issues.append(f"artifact must be a contained ordinary file: {relative}")
        return None
    if not metadata.st_size:
        issues.append(f"empty artifact: {relative}")
        return None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(candidate, flags)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"artifact changed type while reading: {relative}")
        digest = hashlib.sha256()
        size = 0
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
            size += len(block)
        after = os.fstat(stream.fileno())
    if (
        not size
        or (before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_ino, after.st_size, after.st_mtime_ns)
        or size != after.st_size
    ):
        issues.append(f"artifact changed during hashing: {relative}")
        return None
    return {"path": path.as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def git_state(root, issues):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"})

    def run(*args):
        return subprocess.run(
            ["git", "--no-lazy-fetch", "-C", str(root), *args],
            capture_output=True,
            env=env,
            timeout=15,
        )

    try:
        repository = run("rev-parse", "--show-toplevel")
    except FileNotFoundError:
        return {"status": "unavailable", "commit": None, "dirty": None, "provenance": "not_checked"}
    if repository.returncode:
        # If a Git marker exists, command failure is not evidence of a generic folder.
        if any((parent / ".git").exists() for parent in (root, *root.parents)):
            raise ValueError("Git repository inspection failed (Git --no-lazy-fetch required)")
        return {
            "status": "not_repository",
            "commit": None,
            "dirty": None,
            "provenance": "not_checked",
        }
    if Path(repository.stdout.decode("utf-8").strip()).resolve() != root:
        return {
            "status": "outside_selected_scope",
            "commit": None,
            "dirty": None,
            "provenance": "not_checked",
        }
    commit = run("rev-parse", "--verify", "HEAD")
    status = run(
        "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"
    )
    if status.returncode:
        raise ValueError("cannot inspect current Git dirty state")
    dirty = bool(status.stdout)
    if dirty:
        issues.append("Git working tree is dirty (whole repository, including untracked files)")
    if commit.returncode:
        issues.append("Git HEAD commit is unresolved")
    return {
        "status": "checked",
        "commit": commit.stdout.decode("ascii").strip() if not commit.returncode else None,
        "dirty": dirty,
        "provenance": "current_working_tree_only",
    }


def prepare_release(root, version, selected):
    version_string(version)
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("ROOT must be a directory")
    issues = []
    metadata = manifests(root, version, issues)
    changelog = root / "CHANGELOG.md"
    matched = False
    heading = None
    if changelog.exists() or changelog.is_symlink():
        pattern = re.compile(
            r"(?<![A-Za-z0-9_.+-])v?" + re.escape(version) + r"(?![A-Za-z0-9_.+-])"
        )
        fence = None
        for line in read_text(changelog).splitlines():
            marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if marker:
                run, tail = marker.groups()
                if fence is None:
                    fence = run
                elif run[0] == fence[0] and len(run) >= len(fence) and not tail.strip():
                    fence = None
                continue
            if fence is not None:
                continue
            if re.match(r"^ {0,3}#{1,6}\s+", line) and pattern.search(line):
                matched, heading = True, line.strip()
                break
    if not matched:
        issues.append(f"CHANGELOG.md has no Markdown section heading for {version}")
    artifacts = []
    for relative in dict.fromkeys(selected):
        row = artifact(root, relative, issues)
        if row:
            artifacts.append(row)
    git = git_state(root, issues)
    return {
        "schema_version": 1,
        "version": version,
        "local_ready": not issues,
        "readiness_scope": "local_metadata_and_artifact_preflight",
        "manifests": metadata,
        "changelog": {"path": "CHANGELOG.md", "matched": matched, "heading": heading},
        "artifacts": artifacts,
        "git": git,
        "issues": issues,
        "checks_not_run": NOT_RUN[:],
    }


def markdown(report):
    lines = [
        f"# Release preflight {report['version']}",
        "",
        f"Local metadata/artifact ready: {str(report['local_ready']).lower()}",
        f"Git: {json.dumps(report['git'], ensure_ascii=False)}",
        "",
        "Manifest checks:",
    ]
    lines.extend(
        f"- {row['path']}: {row['status']} ({row['version']})" for row in report["manifests"]
    )
    lines.extend(
        ["", f"Changelog section found: {report['changelog']['matched']}", "", "Artifacts:"]
    )
    lines.extend(
        f"- {row['sha256']}  {row['path']} ({row['bytes']} bytes)" for row in report["artifacts"]
    )
    lines.extend(["", "Issues:"])
    lines.extend(f"- {issue}" for issue in report["issues"])
    lines.extend(["", "Checks not run: " + ", ".join(report["checks_not_run"]), ""])
    return "\n".join(lines)


def quiet_stdout():
    # Redirect the actual descriptor so Python's shutdown flush cannot retry a bad pipe.
    try:
        descriptor = os.open(os.devnull, os.O_WRONLY)
        try:
            stdout_descriptor = sys.stdout.fileno()
            os.dup2(descriptor, stdout_descriptor)
        finally:
            if descriptor != 1:
                os.close(descriptor)
    except (OSError, ValueError, TypeError, AttributeError, io.UnsupportedOperation):
        sys.stdout = io.StringIO()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", metavar="ROOT")
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifact", required=True, action="append", metavar="RELATIVE_PATH")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        report = prepare_release(args.root, args.version, args.artifact)
        rendered = (
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.format == "json"
            else markdown(report)
        )
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(rendered)
        sys.stdout.flush()
        return 0 if report["local_ready"] else 1
    except (OSError, ValueError, RecursionError, subprocess.TimeoutExpired) as error:
        quiet_stdout()
        print(f"release preflight input/I/O error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
