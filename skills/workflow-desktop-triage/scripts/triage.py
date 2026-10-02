"""Preview or create classified workspace copies, without deleting originals."""

import argparse
import json
import shutil
import sys
from pathlib import Path

from inventory import digest, inventory


def triage(source, destination, *, apply=False, max_files=1000):
    source, destination = Path(source), Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; select a new folder.")
    report = inventory(source, max_files)
    source = Path(report["root"])
    destination = destination.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("Destination must be outside the source tree.")
    operations = [
        {
            "source": row["path"],
            "destination": row["category"] + "/" + row["path"],
            "sha256": row["sha256"],
        }
        for row in report["files"]
    ]
    result = {
        "schema_version": 1,
        "source_root": str(source),
        "destination_root": str(destination),
        "mode": "copy",
        "applied": False,
        "operations": operations,
        "skipped": report["skipped"],
    }
    if not apply:
        return result
    # Create only one new root; the parent must already exist.
    destination.mkdir()
    try:
        for operation in operations:
            src, dest = source / operation["source"], destination / operation["destination"]
            if src.is_symlink() or not src.is_file() or digest(src)[0] != operation["sha256"]:
                raise ValueError("Source changed after inventory; retry with stable files.")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with src.open("rb") as reader, dest.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            if digest(dest)[0] != operation["sha256"]:
                raise ValueError("Copied bytes differ from inventory; partial output removed.")
        (destination / "copy-ledger.json").write_text(
            json.dumps({**result, "applied": True}, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        shutil.rmtree(destination)
        raise
    result["applied"] = True
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument(
        "--apply", action="store_true", help="Create classified copies in a new folder"
    )
    parser.add_argument("--max-files", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        result = triage(args.source, args.destination, apply=args.apply, max_files=args.max_files)
    except (OSError, ValueError) as exc:
        print("triage: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
