"""Validate meeting-action structure and exact transcript evidence, read-only."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
ISO_TOKEN = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?![\w-])", re.ASCII)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def canonical_date(value):
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def reject_constant(value):
    raise ValueError("Invalid JSON numeric constant: " + value)


def validate(value, transcript):
    report = {"schema_version": 1, "actions": 0, "issues": [], "review_items": []}
    issues = report["issues"]
    if not isinstance(value, dict):
        issues.append("Root must be an object.")
        return report
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        issues.append("schema_version must be the integer 1.")
    meeting = value.get("meeting")
    if not isinstance(meeting, dict):
        issues.append("meeting must be an object with date and timezone fields.")
        meeting = {}
    for key in ("date", "timezone"):
        if key not in meeting:
            issues.append(f"meeting.{key} is required, using null when unknown.")
        elif meeting[key] is not None:
            valid = canonical_date(meeting[key]) if key == "date" else nonempty(meeting[key])
            if not valid:
                issues.append(f"meeting.{key} has an invalid value.")
    items = value.get("actions")
    if not isinstance(items, list):
        issues.append("actions must be an array.")
        return report
    lines = transcript.splitlines(keepends=True)
    seen = set()
    for position, item in enumerate(items, 1):
        report["actions"] += 1
        label = f"Action {position}"
        if not isinstance(item, dict):
            issues.append(label + " must be an object.")
            continue
        identifier = item.get("id")
        if not nonempty(identifier) or identifier in seen:
            issues.append(label + " requires a unique nonempty string id.")
        else:
            seen.add(identifier)
        if not nonempty(item.get("action")):
            issues.append(label + " requires nonempty action text.")
        status = item.get("status")
        if not isinstance(status, str) or status not in {"committed", "proposed"}:
            issues.append(label + " status must be committed or proposed.")
        for key in ("owner", "due_text", "due_date", "resolution_basis"):
            if key not in item:
                issues.append(f"{label} requires {key}, using null when unknown.")
            elif item[key] is not None:
                valid = canonical_date(item[key]) if key == "due_date" else nonempty(item[key])
                if not valid:
                    issues.append(f"{label} {key} has an invalid value.")
            elif key in {"owner", "due_date"}:
                report["review_items"].append(
                    {"id": identifier, "field": key, "reason": f"{key} is unresolved."}
                )
        due_date = item.get("due_date")
        if canonical_date(due_date):
            due_text = item.get("due_text")
            explicit = ISO_TOKEN.findall(due_text) if isinstance(due_text, str) else []
            if explicit:
                if due_date not in explicit:
                    issues.append(
                        label + " due_date does not match an explicit ISO date in due_text."
                    )
            elif not (
                canonical_date(meeting.get("date"))
                and nonempty(meeting.get("timezone"))
                and nonempty(item.get("resolution_basis"))
            ):
                issues.append(
                    label + " date resolution requires meeting.date, meeting.timezone "
                    "and resolution_basis for a relative or unspecified due phrase."
                )
        source = item.get("source")
        if not isinstance(source, dict):
            issues.append(label + " source must be an object.")
            continue
        start, end = source.get("start_line"), source.get("end_line")
        valid_span = type(start) is int and type(end) is int and 1 <= start <= end <= len(lines)
        if not valid_span:
            issues.append(label + " source line bounds must be integers in transcript range.")
        quote = source.get("quote")
        if not nonempty(quote):
            issues.append(label + " source quote must be a nonempty string.")
        elif valid_span and quote not in "".join(lines[start - 1 : end]):
            issues.append(label + " source quote does not occur exactly in its declared line span.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actions_json")
    parser.add_argument("transcript")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args(argv)
    try:
        value = json.loads(
            Path(args.actions_json).read_text(encoding="utf-8"), parse_constant=reject_constant
        )
        transcript = Path(args.transcript).read_text(encoding="utf-8")
        report = validate(value, transcript)
    except (OSError, ValueError, RecursionError) as exc:
        print("actions: " + str(exc), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(
            f"{report['actions']} actions; {len(report['review_items'])} review items; "
            f"{len(report['issues'])} validation issues"
        )
        for issue in report["issues"]:
            print(issue)
        for item in report["review_items"]:
            print(f"Review {item['id']} {item['field']}: {item['reason']}")
    return int(bool(report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
