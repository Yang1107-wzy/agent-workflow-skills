"""Rank a dated skill shortlist using explicit subjective utility/maintenance scores."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ("utility", "portability", "evidence", "complexity", "maintenance")


def rank(value):
    candidates = value.get("candidates") if isinstance(value, dict) else None
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Provide a nonempty candidates array.")
    names = set()
    ranked = []
    for row in candidates:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("name"), str)
            or not row["name"].strip()
            or row["name"] in names
        ):
            raise ValueError("Candidates require unique nonempty names.")
        names.add(row["name"])
        if any(type(row.get(key)) is not int or not 1 <= row[key] <= 5 for key in FIELDS):
            raise ValueError("All rubric scores must be integers 1 through 5.")
        if not isinstance(row.get("overlaps_existing"), bool):
            raise ValueError("overlaps_existing must be boolean.")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("Each candidate requires dated sources.")
        for source in sources:
            if not isinstance(source, dict) or source.get("access") not in (
                "fetched",
                "indexed",
                "unavailable",
            ):
                raise ValueError("Source access must be fetched, indexed or unavailable.")
            url = source.get("url")
            if not isinstance(url, str):
                raise ValueError("Source URL must be a string.")
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ValueError("Source URL requires HTTP(S) and a hostname.")
            try:
                date.fromisoformat(source.get("checked_on", ""))
            except (ValueError, TypeError):
                raise ValueError("checked_on must be YYYY-MM-DD.") from None
        score = (
            2 * row["utility"]
            + row["portability"]
            + row["evidence"]
            - row["complexity"]
            - row["maintenance"]
            - (5 if row["overlaps_existing"] else 0)
        )
        ranked.append(
            {
                **row,
                "score": score,
                "fetched_sources": sum(s["access"] == "fetched" for s in sources),
            }
        )
    ranked.sort(key=lambda row: (-row["score"], row["name"]))
    return {
        "schema_version": 1,
        "rubric": "2*utility + portability + evidence - complexity - maintenance - 5*overlap",
        "note": "Scores are editorial judgments, not an objective popularity or quality measurement. Source access is caller-declared.",
        "ranked": ranked,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates")
    args = parser.parse_args(argv)
    try:
        result = rank(json.loads(Path(args.candidates).read_text(encoding="utf-8")))
    except (OSError, ValueError, RecursionError) as exc:
        print("rank: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
