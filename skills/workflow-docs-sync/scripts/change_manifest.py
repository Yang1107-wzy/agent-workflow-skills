"""Emit a read-only manifest for two explicit commits and separate worktree state."""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def path_fields(raw, key="path"):
    """Expose UTF-8 names directly, preserving other byte sequences losslessly."""
    try:
        return {key: raw.decode("utf-8")}
    except UnicodeDecodeError:
        return {key: None, key + "_bytes_base64": base64.b64encode(raw).decode("ascii")}


def nul_fields(raw):
    if not raw:
        return []
    if not raw.endswith(b"\0"):
        raise ValueError("Incomplete NUL-delimited Git output.")
    fields = raw[:-1].split(b"\0")
    if any(not field for field in fields):
        raise ValueError("Empty field in Git output.")
    return fields


def parse_commit_changes(raw):
    fields = nul_fields(raw)
    rows = []
    index = 0
    while index < len(fields):
        status = fields[index]
        if not re.fullmatch(rb"(?:[ADMTUXB]|[RC][0-9]{1,3})", status):
            raise ValueError("Unexpected Git diff status.")
        renamed = status[:1] in (b"R", b"C")
        count = 3 if renamed else 2
        if index + count > len(fields):
            raise ValueError("Incomplete Git diff path record.")
        row = {"status": status.decode("ascii"), **path_fields(fields[index + count - 1])}
        if renamed:
            row.update(path_fields(fields[index + 1], "old_path"))
        rows.append(row)
        index += count
    return rows


def parse_working_tree(raw):
    fields = nul_fields(raw)
    state = {"tracked": [], "untracked": []}
    index = 0
    while index < len(fields):
        field = fields[index]
        if len(field) < 4 or field[2:3] != b" ":
            raise ValueError("Incomplete Git working-tree record.")
        status, name = field[:2], field[3:]
        if not re.fullmatch(rb"[ MADRCUT?!]{2}", status):
            raise ValueError("Unexpected Git working-tree status.")
        row = {"status": status.decode("ascii"), **path_fields(name)}
        if b"R" in status or b"C" in status:
            index += 1
            if index >= len(fields):
                raise ValueError("Incomplete Git working-tree rename.")
            row.update(path_fields(fields[index], "old_path"))
        state["untracked" if status == b"??" else "tracked"].append(row)
        index += 1
    return state


def documentation_candidates(raw):
    candidates = []
    conventional = {b"readme", b"contributing", b"changelog", b"changes", b"history"}
    for name in nul_fields(raw):
        parts = name.lower().split(b"/")
        stem = parts[-1].split(b".", 1)[0]
        if stem in conventional:
            reason = "conventional_documentation_filename"
        elif b"docs" in parts[:-1]:
            reason = "docs_directory"
        else:
            continue
        candidates.append({**path_fields(name), "reason": reason})
    return candidates


def change_manifest(repository, base, head):
    root = Path(repository).resolve()
    if not root.is_dir():
        raise ValueError("Repository directory does not exist.")
    for revision in (base, head):
        if not revision or revision.startswith("-") or "\0" in revision:
            raise ValueError("Supply a nonempty commit revision that does not start with '-'.")

    environment = dict(os.environ)
    for variable in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
    ):
        environment.pop(variable, None)
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1")

    def git(*args):
        result = subprocess.run(
            [
                "git",
                "--no-lazy-fetch",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                *args,
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            raise ValueError(
                "Git read failed; require Git supporting --no-lazy-fetch, "
                "a working-tree repository and available commit objects."
            )
        return result.stdout

    top = git("rev-parse", "--show-toplevel").removesuffix(b"\n")
    if Path(os.fsdecode(top)).resolve() != root:
        raise ValueError("Select the repository root, not a nested directory.")

    def resolve(revision):
        raw = git("rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
        commit = raw.strip().decode("ascii")
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise ValueError("Git did not resolve one commit object.")
        return commit

    base_commit, head_commit = resolve(base), resolve(head)
    changes = parse_commit_changes(
        git(
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-status",
            "-z",
            "--find-renames",
            base_commit,
            head_commit,
            "--",
        )
    )
    state = parse_working_tree(git("status", "--porcelain=v1", "-z", "--untracked-files=all"))
    candidates = documentation_candidates(git("ls-tree", "-r", "--name-only", "-z", head_commit))
    return {
        "schema_version": 1,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "commit_changes": changes,
        "working_tree": state,
        "candidate_documentation_basis": "head_tree_conventions_only",
        "candidate_documentation_paths": candidates,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("--base", required=True, help="Explicit base commit revision")
    parser.add_argument("--head", required=True, help="Explicit head commit revision")
    args = parser.parse_args(argv)
    try:
        report = change_manifest(args.repository, args.base, args.head)
    except (OSError, ValueError) as exc:
        print("change-manifest: " + str(exc), file=sys.stderr)
        return 2

    def redirect_stdout_to_devnull():
        try:
            stdout_fd = sys.stdout.fileno()
            null_fd = os.open(os.devnull, os.O_WRONLY)
            if null_fd == stdout_fd:
                return
            try:
                os.dup2(null_fd, stdout_fd)
            finally:
                os.close(null_fd)
        except OSError:
            pass

    try:
        sys.stdout.buffer.write(
            (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        redirect_stdout_to_devnull()
        return 2
    except OSError as exc:
        redirect_stdout_to_devnull()
        print("change-manifest: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
