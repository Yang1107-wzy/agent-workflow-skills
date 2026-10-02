"""Read-only UTF-8 literal-anchor checks; semantic fidelity requires separate review."""

import argparse
import json
import os
import sys
from pathlib import Path

KINDS = {"number", "date", "name", "status", "term", "other"}
SCOPE = "Literal occurrence evidence only; no semantic, translation or factual certification."


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("JSON object keys must be unique: " + key)
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError("Invalid JSON constant: " + value)


def validate_map(value):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int:
        raise ValueError("Map must be an object with integer schema_version=1.")
    if value["schema_version"] != 1:
        raise ValueError("Map schema_version must equal 1.")
    items = value.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Map items must be a nonempty array.")
    seen = set()
    for position, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Item {position} must be an object.")
        for field in ("id", "source", "target", "kind"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"Item {position}: {field} must be a nonempty string.")
        if item["id"] in seen:
            raise ValueError("Item IDs must be unique: " + item["id"])
        seen.add(item["id"])
        if item["kind"] not in KINDS:
            raise ValueError("Unknown kind for " + item["id"])
        if "factual_change" in item and type(item["factual_change"]) is not bool:
            raise ValueError("factual_change must be a boolean: " + item["id"])
        explanation = item.get("explanation")
        if "explanation" in item or item.get("factual_change", False):
            if not isinstance(explanation, str) or not explanation.strip():
                raise ValueError("A nonempty explanation is required: " + item["id"])
    return items


def check(source, edited, items):
    report = {"schema_version": 1, "scope": SCOPE, "evidence": [], "issues": []}
    for item in items:
        source_count = source.count(item["source"])
        target_count = edited.count(item["target"])
        evidence = {field: item[field] for field in ("id", "source", "target", "kind")}
        evidence.update(source_count=source_count, target_count=target_count)
        for field in ("factual_change", "explanation"):
            if field in item:
                evidence[field] = item[field]
        report["evidence"].append(evidence)
        findings = []
        if source_count == 0:
            findings.append(("source_missing", "Source literal is absent."))
        if target_count == 0:
            findings.append(("target_missing", "Target literal is absent."))
        if source_count != target_count:
            findings.append(("count_mismatch", "Literal occurrence counts differ."))
        for code, message in findings:
            report["issues"].append({"id": item["id"], "code": code, "message": message})
    return report


def render_text(report):
    lines = [report["scope"]]
    for evidence in report["evidence"]:
        lines.append(
            f"{evidence['id']} ({evidence['kind']}): "
            f"source={evidence['source_count']} target={evidence['target_count']}"
        )
        if "explanation" in evidence:
            lines.append("  explanation: " + evidence["explanation"])
    for issue in report["issues"]:
        lines.append(f"{issue['id']}: {issue['code']}: {issue['message']}")
    return "\n".join(lines)


def silence_stdout():
    # Prevent CPython's shutdown flush from retrying a broken output pipe.
    try:
        descriptor = sys.stdout.fileno()
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), descriptor)
    except (AttributeError, OSError, ValueError):
        sys.stdout = None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("edited")
    parser.add_argument("map_json")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    try:
        with Path(args.source).open(encoding="utf-8", newline="") as source_file:
            source = source_file.read()
        with Path(args.edited).open(encoding="utf-8", newline="") as edited_file:
            edited = edited_file.read()
        value = json.loads(
            Path(args.map_json).read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        report = check(source, edited, validate_map(value))
        output = (
            json.dumps(report, ensure_ascii=False, indent=2)
            if args.format == "json"
            else render_text(report)
        )
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(output)
        sys.stdout.flush()
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        silence_stdout()
        try:
            print("preservation: " + str(exc), file=sys.stderr)
            sys.stderr.flush()
        except (OSError, UnicodeError):
            pass
        return 2
    return int(bool(report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
