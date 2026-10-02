import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/workflow-meeting-actions/scripts/validate_actions.py"
TRANSCRIPT = (
    "Meeting date: 2026-10-02; timezone: Asia/Tokyo\n"
    "Mira: I will send the revised budget by 2026-10-09.\n"
    "Leo: The onboarding experience could be better.\n"
    "Mira: We could draft an onboarding checklist; no owner yet.\n"
    "Leo: I will compare the vendor quotes.\n"
    "Mira: I will send the notes next Friday.\n"
)


def action(**changes):
    value = {
        "id": "a1",
        "action": "Send the revised budget",
        "status": "committed",
        "owner": "Mira",
        "due_text": "by 2026-10-09",
        "due_date": "2026-10-09",
        "resolution_basis": None,
        "source": {
            "start_line": 2,
            "end_line": 2,
            "quote": "Mira: I will send the revised budget by 2026-10-09.",
        },
    }
    value.update(changes)
    return value


def document(*items, meeting=None):
    return {
        "schema_version": 1,
        "meeting": meeting if meeting is not None else {"date": None, "timezone": None},
        "actions": list(items) if items else [action()],
    }


class MeetingActionsTests(unittest.TestCase):
    def check(self, value, transcript=TRANSCRIPT, raw=False, output_format="json"):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "actions.json"
            source = Path(directory) / "transcript.txt"
            ledger.write_text(value if raw else json.dumps(value), encoding="utf-8")
            source.write_text(transcript, encoding="utf-8")
            before = {path.name: path.read_bytes() for path in (ledger, source)}
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(ledger), str(source), "--format", output_format],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(before, {path.name: path.read_bytes() for path in (ledger, source)})
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), sorted(before))
            return result

    def assert_invalid(self, value, fragment):
        result = self.check(value)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(fragment, " ".join(json.loads(result.stdout)["issues"]))

    def test_explicit_date_without_context_is_valid(self):
        result = self.check(document())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["review_items"], [])
        self.assertEqual(report["actions"], 1)

    def test_quote_mismatch_is_invalid(self):
        self.assert_invalid(
            document(
                action(
                    source={"start_line": 2, "end_line": 2, "quote": "Mira: Budget was approved."}
                )
            ),
            "quote",
        )

    def test_line_bounds_reject_boolean_zero_reversed_and_out_of_range(self):
        for start, end in [(True, 2), (2, False), (0, 2), (3, 2), (2, 7), ("2", 2)]:
            with self.subTest(start=start, end=end):
                self.assert_invalid(
                    document(
                        action(source={"start_line": start, "end_line": end, "quote": "Mira:"})
                    ),
                    "line",
                )

    def test_quote_must_be_in_declared_span(self):
        self.assert_invalid(
            document(action(source={"start_line": 3, "end_line": 3, "quote": "by 2026-10-09"})),
            "quote",
        )

    def test_unknown_owner_and_due_date_are_allowed_and_visible(self):
        result = self.check(
            document(action(status="proposed", owner=None, due_text=None, due_date=None))
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["issues"], [])
        self.assertEqual({item["field"] for item in report["review_items"]}, {"owner", "due_date"})
        self.assertTrue(all(item["id"] == "a1" for item in report["review_items"]))

    def test_resolved_relative_date_requires_all_context_fields(self):
        relative = action(
            due_text="next Friday",
            resolution_basis="User confirmed 2026-10-09",
            source={"start_line": 6, "end_line": 6, "quote": "next Friday"},
        )
        context = {"date": "2026-10-02", "timezone": "Asia/Tokyo"}
        for missing in ["date", "timezone", "resolution_basis"]:
            with self.subTest(missing=missing):
                item, meeting = copy.deepcopy(relative), dict(context)
                (item if missing == "resolution_basis" else meeting)[missing] = None
                self.assert_invalid(document(item, meeting=meeting), "resolution")

    def test_supported_relative_date_is_valid_without_natural_language_parsing(self):
        result = self.check(
            document(
                action(
                    due_text="after the release freeze",
                    resolution_basis="User confirmed the exact date",
                ),
                meeting={"date": "2026-10-02", "timezone": "Asia/Tokyo"},
            )
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unspecified_phrase_cannot_resolve_without_context(self):
        self.assert_invalid(document(action(due_text=None)), "resolution")

    def test_explicit_date_mismatch_is_invalid(self):
        self.assert_invalid(document(action(due_date="2026-10-10")), "due_date")

    def test_duplicate_ids_are_invalid(self):
        self.assert_invalid(document(action(), action()), "unique")

    def test_canonical_gregorian_dates_required(self):
        for date in ["2026-02-29", "2026-2-03", "20261009", "0000-01-01", "2026-10-09T12:00"]:
            with self.subTest(date=date):
                self.assert_invalid(document(action(due_date=date)), "due_date")
                self.assert_invalid(
                    document(meeting={"date": date, "timezone": None}), "meeting.date"
                )

    def test_valid_leap_day_and_multiline_exact_quote(self):
        quote = "Mira: I will send it\nby 2028-02-29."
        result = self.check(
            document(
                action(
                    due_text="2028-02-29",
                    due_date="2028-02-29",
                    source={"start_line": 1, "end_line": 2, "quote": quote},
                )
            ),
            transcript=quote + "\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_required_nullable_fields_cannot_be_omitted(self):
        for key in ["owner", "due_text", "due_date", "resolution_basis", "source"]:
            with self.subTest(key=key):
                item = action()
                del item[key]
                self.assert_invalid(document(item), key)

    def test_malformed_shapes_are_findings_not_tracebacks(self):
        values = [
            [],
            None,
            {},
            {"schema_version": True, "meeting": {}, "actions": []},
            {"schema_version": 1, "meeting": [], "actions": []},
            {"schema_version": 1, "meeting": {}, "actions": {}},
            document(None),
            document(action(status=[])),
            document(action(source=[])),
            document(action(owner=[])),
            document(action(due_text=" ")),
            document(action(action=" ")),
            document(action(id=" ")),
            document(action(source={"start_line": 2, "end_line": 2, "quote": ""})),
        ]
        for value in values:
            with self.subTest(value=value):
                result = self.check(value)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(json.loads(result.stdout)["issues"])
                self.assertNotIn("Traceback", result.stderr)

    def test_malformed_json_returns_two_and_preserves_sources(self):
        result = self.check('{"actions":', raw=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_non_json_number_constants_return_two(self):
        for constant in ["NaN", "Infinity", "-Infinity"]:
            with self.subTest(constant=constant):
                value = json.dumps(document()).replace(
                    '"schema_version": 1', '"schema_version": ' + constant
                )
                result = self.check(value, raw=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_invalid_utf8_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "transcript.txt"
            ledger = Path(directory) / "actions.json"
            source.write_bytes(b"\xff")
            ledger.write_text(json.dumps(document()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(ledger), str(source)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(source.read_bytes(), b"\xff")

    def test_usage_and_missing_files_return_two(self):
        for arguments in [[], ["/nonexistent/actions.json", "/nonexistent/transcript.txt"]]:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), *arguments], capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_text_output_displays_review_items(self):
        result = self.check(document(action(owner=None, due_date=None)), output_format="text")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("a1", result.stdout)
        self.assertIn("owner", result.stdout)
        self.assertIn("due_date", result.stdout)


if __name__ == "__main__":
    unittest.main()
