import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/workflow-experiment-report/scripts/summarize_results.py"


class ExperimentReportTests(unittest.TestCase):
    def run_report(self, raw, expected=5, output_format="json", extra=()):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "results.jsonl"
            source.write_text(raw, encoding="utf-8")
            before = source.read_bytes()
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(source),
                    "--metric",
                    "score",
                    "--expected-cases",
                    str(expected),
                    "--unit",
                    "points",
                    "--protocol",
                    "fixed-v1",
                    "--format",
                    output_format,
                    *extra,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual([p.name for p in Path(directory).iterdir()], ["results.jsonl"])
            return result

    def report(self, raw, **kwargs):
        result = self.run_report(raw, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def assert_invalid(self, raw, **kwargs):
        result = self.run_report(raw, **kwargs)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_coverage_distinguishes_failed_and_missing_expected(self):
        raw = '{"id":"a","score":2}\n{"id":"b","score":4}\n{"id":"c","score":null}\n'
        report = self.report(raw)
        self.assertEqual(
            report["counts"],
            {
                "observed": 3,
                "expected": 5,
                "returned": 2,
                "failed": 1,
                "missing": 2,
            },
        )
        self.assertEqual(
            report["coverage"],
            {
                "numerator": 2,
                "denominator": 5,
                "fraction": 0.4,
            },
        )
        self.assertEqual(
            report["statistics"],
            {
                "mean": 3.0,
                "median": 3.0,
                "min": 2.0,
                "max": 4.0,
                "denominator": 2,
                "population": "returned measurements only",
            },
        )
        self.assertEqual(report["metric"], "score")
        self.assertEqual(report["unit"], "points")
        self.assertEqual(report["protocol"], "fixed-v1")
        self.assertEqual(report["source"]["sha256"], hashlib.sha256(raw.encode()).hexdigest())

    def test_true_zero_and_negative_values_are_measurements(self):
        report = self.report('{"id":0,"score":0}\n{"id":-2,"score":-4}\n', expected=2)
        self.assertEqual(report["counts"]["returned"], 2)
        self.assertEqual(report["coverage"]["fraction"], 1)
        self.assertEqual(report["statistics"]["mean"], -2)
        self.assertEqual(report["statistics"]["max"], 0)

    def test_all_failed_still_has_usable_report(self):
        report = self.report('{"id":"a","score":null}\n', expected=3)
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertEqual(report["counts"]["missing"], 2)
        self.assertEqual(report["coverage"]["fraction"], 0)
        for name in ["mean", "median", "min", "max"]:
            self.assertIsNone(report["statistics"][name])

    def test_empty_source_means_all_expected_cases_are_missing(self):
        report = self.report("", expected=2)
        self.assertEqual(report["counts"]["observed"], 0)
        self.assertEqual(report["counts"]["missing"], 2)
        self.assertIsNone(report["statistics"]["mean"])

    def test_duplicate_ids_are_rejected(self):
        for id_value in ['"a"', "7"]:
            with self.subTest(id_value=id_value):
                self.assert_invalid("\n".join(['{"id":' + id_value + ',"score":0}'] * 2))

    def test_string_and_integer_ids_are_distinct(self):
        report = self.report('{"id":1,"score":0}\n{"id":"1","score":0}\n')
        self.assertEqual(report["counts"]["observed"], 2)

    def test_unicode_line_separator_inside_json_string_is_not_a_row_boundary(self):
        report = self.report('{"id":"a\u2028b","score":0}\n')
        self.assertEqual(report["counts"]["observed"], 1)

    def test_deep_invalid_input_returns_two_without_traceback(self):
        self.assert_invalid("[" * 2000 + "0" + "]" * 2000)

    def test_missing_fields_bad_shapes_and_invalid_ids_are_rejected(self):
        rows = [
            {},
            {"id": "a"},
            {"score": 3},
            [],
            None,
            {"id": True, "score": 3},
            {"id": False, "score": 3},
            {"id": 1.0, "score": 3},
            {"id": "", "score": 3},
            {"id": "  ", "score": 3},
            {"id": [], "score": 3},
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assert_invalid(json.dumps(row))

    def test_boolean_nonfinite_and_nonnumeric_metrics_are_rejected(self):
        for token in ["true", "false", "NaN", "Infinity", "-Infinity", "1e400", '"1"', "{}", "[]"]:
            with self.subTest(token=token):
                self.assert_invalid('{"id":"a","score":' + token + "}\n")

    def test_decimal_digit_loss_and_underflow_are_rejected(self):
        for token in ["0.1234567890123456789", "9007199254740993.0", "1e-400", "2e-324"]:
            with self.subTest(token=token):
                self.assert_invalid('{"id":"a","score":' + token + "}\n")

    def test_ordinary_decimal_and_equivalent_decimal_spelling_are_supported(self):
        report = self.report('{"id":"a","score":0.10}\n{"id":"b","score":2e-1}\n')
        self.assertEqual(report["statistics"]["mean"], 0.15)

    def test_population_summaries_avoid_intermediate_float_overflow(self):
        report = self.report('{"id":"a","score":1e308}\n{"id":"b","score":1e308}\n')
        self.assertEqual(report["statistics"]["mean"], 10**308)
        self.assertEqual(report["statistics"]["median"], 10**308)

    def test_large_odd_integers_and_integral_aggregates_remain_exact(self):
        report = self.report(
            '{"id":"a","score":9007199254740993}\n{"id":"b","score":9007199254740995}\n'
        )
        self.assertEqual(report["statistics"]["min"], 9007199254740993)
        self.assertEqual(report["statistics"]["max"], 9007199254740995)
        self.assertEqual(report["statistics"]["mean"], 9007199254740994)
        self.assertEqual(report["statistics"]["median"], 9007199254740994)
        self.assertIsInstance(report["statistics"]["mean"], int)

    def test_small_decimal_measurements_remain_nonzero(self):
        report = self.report('{"id":"a","score":5e-324}\n', expected=1)
        self.assertEqual(report["statistics"]["mean"], 5e-324)
        self.assertEqual(report["counts"]["returned"], 1)

    def test_aggregate_underflow_is_rejected_instead_of_becoming_zero(self):
        self.assert_invalid(
            '{"id":"a","score":5e-324}\n{"id":"b","score":0}\n{"id":"c","score":0}\n'
        )

    def test_invalid_json_blank_rows_duplicate_keys_and_encoding_are_rejected(self):
        for raw in [
            '{"id":',
            "\n",
            '{"id":"a","score":1}\n\n',
            '{"id":"a","score":1,"score":2}',
            '{"id":"a","score":1}\nnot-json',
        ]:
            with self.subTest(raw=raw):
                self.assert_invalid(raw)

    def test_expected_cases_must_be_positive_and_at_least_observed_rows(self):
        raw = '{"id":"a","score":1}\n{"id":"b","score":null}\n'
        for expected in [0, -1, 1, "1.5", "true"]:
            with self.subTest(expected=expected):
                self.assert_invalid(raw, expected=expected)

    def test_metadata_must_be_nonempty(self):
        for option in ["--metric", "--unit", "--protocol"]:
            with self.subTest(option=option):
                self.assert_invalid('{"id":"a","score":1}', extra=(option, " "))

    def test_markdown_reports_both_denominators_without_success_claims(self):
        result = self.run_report(
            '{"id":"a","score":0}\n{"id":"b","score":null}\n', expected=4, output_format="markdown"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/4", result.stdout)
        self.assertIn("1 returned measurement", result.stdout)
        self.assertIn("failed", result.stdout)
        self.assertIn("missing", result.stdout)
        self.assertNotIn("success", result.stdout.lower())

    def test_missing_source_and_invalid_utf8_return_two(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.jsonl"
            for content in [None, b"\xff"]:
                if content is not None:
                    source.write_bytes(content)
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        str(source),
                        "--metric",
                        "score",
                        "--expected-cases",
                        "2",
                        "--unit",
                        "points",
                        "--protocol",
                        "v1",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                if content is not None:
                    self.assertEqual(source.read_bytes(), content)

    def test_unit_parser_preserves_valid_numbers_and_rejects_loss(self):
        self.assertTrue(SCRIPT.is_file(), "helper has not been implemented")
        spec = importlib.util.spec_from_file_location("experiment_report", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.parse_decimal("0.1"), 0.1)
        self.assertEqual(module.parse_integer("0"), 0)
        for token in ["1e-400", "0.1234567890123456789"]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                module.parse_decimal(token)
        self.assertEqual(module.parse_integer("9007199254740993"), 9007199254740993)


if __name__ == "__main__":
    unittest.main()
