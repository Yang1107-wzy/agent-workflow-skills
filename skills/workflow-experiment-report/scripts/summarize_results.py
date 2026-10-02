#!/usr/bin/env python3
"""Read-only JSONL population summaries; exit 0 for a report, 2 for invalid input."""

import argparse
import hashlib
import html
import json
import math
import sys
from decimal import Decimal
from fractions import Fraction
from pathlib import Path


def parse_integer(token):
    """JSON integer tokens stay exact, including values beyond float's mantissa."""
    return int(token)


def parse_decimal(token):
    """Require finite float conversion that preserves the source decimal value."""
    value = float(token)
    if not math.isfinite(value) or Decimal(token) != Decimal(str(value)):
        raise ValueError(f"unsupported numeric precision or nonfinite value: {token}")
    return value


def reject_constant(token):
    raise ValueError(f"nonfinite JSON number: {token}")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def output_number(value):
    """Keep integral summaries exact; round nonintegral summaries to finite float."""
    if value.denominator == 1:
        return value.numerator
    converted = float(value)
    if not math.isfinite(converted) or (converted == 0 and value != 0):
        raise ValueError("aggregate has unsupported overflow or underflow")
    return converted


def summarize(raw, source, metric, expected, unit, protocol):
    if expected <= 0:
        raise ValueError("expected-cases must be positive")
    for name, value in [("metric", metric), ("unit", unit), ("protocol", protocol)]:
        if not value.strip():
            raise ValueError(f"{name} must be nonempty")

    text = raw.decode("utf-8")
    lines = text.split("\n") if text else []
    if lines and lines[-1] == "":
        lines.pop()  # A terminal newline ends the last row; interior blanks remain errors.
    seen = set()
    measurements = []
    observed = failed = 0
    for line_number, line in enumerate(lines, 1):
        try:
            row = json.loads(
                line,
                parse_int=parse_integer,
                parse_float=parse_decimal,
                parse_constant=reject_constant,
                object_pairs_hook=unique_keys,
            )
            if not isinstance(row, dict):
                raise ValueError("each row must be a JSON object")
            identifier = row.get("id")
            if type(identifier) not in (int, str) or (
                isinstance(identifier, str) and not identifier.strip()
            ):
                raise ValueError("id must be a nonempty string or integer, excluding bool")
            identity = (type(identifier), identifier)
            if identity in seen:
                raise ValueError(f"duplicate id: {identifier!r}")
            seen.add(identity)
            if metric not in row:
                raise ValueError(f"missing metric key: {metric}")
            value = row[metric]
            if value is None:
                failed += 1
            elif type(value) in (int, float):
                measurements.append(value)
            else:
                raise ValueError("metric must be a finite JSON number or null")
            observed += 1
        except (ValueError, OverflowError) as error:
            raise ValueError(f"line {line_number}: {error}") from error

    if observed > expected:
        raise ValueError("expected-cases must be at least the observed row count")
    returned = len(measurements)
    ordered = sorted(Fraction(str(value)) for value in measurements)
    statistics = dict.fromkeys(("mean", "median", "min", "max"))
    if returned:
        middle = returned // 2
        median = ordered[middle] if returned % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        statistics.update(
            mean=output_number(sum(ordered, Fraction(0)) / returned),
            median=output_number(median),
            min=min(measurements),
            max=max(measurements),
        )
    statistics.update(denominator=returned, population="returned measurements only")
    return {
        "schema_version": 1,
        "source": {"path": str(source), "sha256": hashlib.sha256(raw).hexdigest()},
        "metric": metric,
        "unit": unit,
        "protocol": protocol,
        "counts": {
            "observed": observed,
            "expected": expected,
            "returned": returned,
            "failed": failed,
            "missing": expected - observed,
        },
        "coverage": {
            "numerator": returned,
            "denominator": expected,
            "fraction": output_number(Fraction(returned, expected)),
        },
        "statistics": statistics,
        "numeric_precision": (
            "Integer inputs and integral aggregates are exact. Decimal float inputs must "
            "round-trip to the same decimal value. Nonintegral aggregates are rounded to "
            "binary64; nonfinite output and nonzero-to-zero underflow are rejected."
        ),
    }


def markdown(report):
    def escape(value):
        return html.escape(str(value)).replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")

    counts, stats = report["counts"], report["statistics"]
    rows = [
        "# Experiment summary",
        "",
        f"Source: {escape(report['source']['path'])}",
        f"SHA-256: {report['source']['sha256']}",
        "",
        f"Metric: {escape(report['metric'])}; unit: {escape(report['unit'])}; "
        f"protocol: {escape(report['protocol'])}",
        "",
        "| Count | Value |",
        "| --- | ---: |",
        *[
            f"| {name} | {counts[name]} |"
            for name in ("observed", "expected", "returned", "failed", "missing")
        ],
        "",
        f"Measurement coverage: {counts['returned']}/{counts['expected']} "
        f"({report['coverage']['fraction']}).",
        "",
        f"Statistics conditioned on {counts['returned']} returned measurement(s); "
        "null failures and missing expected cases are excluded from this denominator.",
        "",
        "| Statistic | Value |",
        "| --- | ---: |",
        *[
            f"| {name} | {stats[name] if stats[name] is not None else 'null (no measurements)'} |"
            for name in ("mean", "median", "min", "max")
        ],
        "",
        "Failed = explicit null metric; missing = expected cases without a source row. "
        "A returned measurement does not establish task quality or correctness.",
        "",
        "These are descriptive population summaries. No uncertainty, significance, "
        "or causal improvement is estimated. Protocol and expected case count are supplied "
        "by the caller and require source evidence.",
        "",
        report["numeric_precision"],
        "",
    ]
    return "\n".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_jsonl", type=Path)
    parser.add_argument("--metric", required=True)
    parser.add_argument("--expected-cases", required=True, type=int)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        report = summarize(
            args.results_jsonl.read_bytes(),
            args.results_jsonl,
            args.metric,
            args.expected_cases,
            args.unit,
            args.protocol,
        )
        output = (
            json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            if args.format == "json"
            else markdown(report)
        )
    except (OSError, ValueError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
