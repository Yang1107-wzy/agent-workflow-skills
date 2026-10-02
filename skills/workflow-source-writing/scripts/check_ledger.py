"""Validate evidence-ledger structure. This does not fact-check source contents."""

import argparse
import json
import sys
from pathlib import Path

STATUSES = {"supported", "provided", "inference", "unverified"}


def validate(value):
    result = {"schema_version": 1, "claims": 0, "unverified": 0, "issues": []}
    claims = value.get("claims") if isinstance(value, dict) else None
    if not isinstance(claims, list):
        result["issues"].append("Root must contain a claims array.")
        return result
    seen = set()
    for position, claim in enumerate(claims, 1):
        result["claims"] += 1
        label = f"Claim {position}"
        if not isinstance(claim, dict):
            result["issues"].append(label + " must be an object.")
            continue
        identifier = claim.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            result["issues"].append(label + " requires a unique nonempty string id.")
        else:
            seen.add(identifier)
        if not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
            result["issues"].append(label + " requires claim text.")
        status = claim.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            result["issues"].append(label + " has an invalid status.")
        if status == "unverified":
            result["unverified"] += 1
        evidence = claim.get("evidence")
        if not isinstance(evidence, list):
            result["issues"].append(label + " requires an evidence array.")
            continue
        observed = 0
        for item in evidence:
            if (
                not isinstance(item, dict)
                or any(
                    not isinstance(item.get(k), str) or not item[k].strip()
                    for k in ("source", "locator", "observation")
                )
                or not isinstance(item.get("observed"), bool)
            ):
                result["issues"].append(label + " has incomplete evidence metadata.")
            elif item["observed"]:
                observed += 1
        if status == "supported" and not observed:
            result["issues"].append(label + " is supported without any observed evidence.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        value = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        report = validate(value)
    except (OSError, ValueError, RecursionError) as exc:
        print("ledger: " + str(exc), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(
            f"{report['claims']} claims; {report['unverified']} unverified; {len(report['issues'])} structural issues"
        )
        for issue in report["issues"]:
            print(issue)
    return int(bool(report["issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
