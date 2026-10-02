import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/workflow-bilingual-edit"
SCRIPT = SKILL / "scripts/check_preservation.py"
SOURCE = "青灯项目仍处于试验阶段。2026-09-01，林河测量了 12 ms 的延迟；结果可能改善。"
EDITED = (
    "The Qingdeng Project remains experimental. On 2026-09-01, Lin He measured "
    "a latency of 12 ms; the results may improve."
)


def item(**changes):
    value = {"id": "project", "source": "青灯项目", "target": "Qingdeng Project", "kind": "name"}
    value.update(changes)
    return value


def mapping(*items):
    return {"schema_version": 1, "items": list(items) if items else [item()]}


class BilingualEditTests(unittest.TestCase):
    def check(self, value, source=SOURCE, edited=EDITED, raw=False, fmt="json", script=SCRIPT):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("source.txt", "edited.txt", "map.json")]
            for path, text in zip(
                paths, (source, edited, value if raw else json.dumps(value)), strict=True
            ):
                path.write_text(text, encoding="utf-8")
            before = {path.name: path.read_bytes() for path in paths}
            result = subprocess.run(
                [sys.executable, str(script), *map(str, paths), "--format", fmt],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(before, {path.name: path.read_bytes() for path in paths})
            self.assertEqual(
                sorted(before), sorted(path.name for path in Path(directory).iterdir())
            )
            self.assertNotIn("can't open file", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            return result

    def assert_invalid(self, value, fragment=None, raw=False):
        result = self.check(value, raw=raw)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("preservation:", result.stderr)
        if fragment:
            self.assertIn(fragment, result.stderr)

    def test_chinese_to_english_names_and_units_have_evidence(self):
        result = self.check(
            mapping(item(), item(id="latency", source="12 ms", target="12 ms", kind="number"))
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["evidence"][0]["source_count"], 1)
        self.assertEqual(report["evidence"][1]["target_count"], 1)
        self.assertIn("semantic", report["scope"])

    def test_english_to_chinese_status_anchor(self):
        result = self.check(
            mapping(item(source="remains experimental", target="仍处于试验阶段", kind="status")),
            source=EDITED,
            edited=SOURCE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_numeric_anchor_is_issue(self):
        result = self.check(
            mapping(item(source="12 ms", target="12 ms", kind="number")),
            edited=EDITED.replace("12 ms", "20 ms"),
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "target_missing", {issue["code"] for issue in json.loads(result.stdout)["issues"]}
        )

    def test_extra_duplicate_target_is_issue(self):
        result = self.check(mapping(), edited=EDITED + " Qingdeng Project")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "count_mismatch", {issue["code"] for issue in json.loads(result.stdout)["issues"]}
        )

    def test_dropped_repeat_is_issue(self):
        result = self.check(mapping(), source=SOURCE + " 青灯项目")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["evidence"][0]["source_count"], 2)

    def test_stale_source_anchor_is_issue_even_if_target_exists(self):
        result = self.check(mapping(item(source="不存在")))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "source_missing", {issue["code"] for issue in json.loads(result.stdout)["issues"]}
        )

    def test_same_literal_is_valid_without_translation(self):
        result = self.check(mapping(item(source="2026-09-01", target="2026-09-01", kind="date")))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_literal_matching_preserves_physical_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.txt"
            edited_path = Path(directory) / "edited.txt"
            map_path = Path(directory) / "map.json"
            source_path.write_bytes(b"12\r\nms")
            edited_path.write_bytes(b"12\r\nms")
            for target, expected_returncode, expected_count in [
                ("12\r\nms", 0, 1),
                ("12\nms", 1, 0),
            ]:
                with self.subTest(target=repr(target)):
                    map_path.write_text(
                        json.dumps(mapping(item(source="12\r\nms", target=target))),
                        encoding="utf-8",
                    )
                    arguments = [
                        sys.executable,
                        str(SCRIPT),
                        *map(str, (source_path, edited_path, map_path)),
                    ]
                    result = subprocess.run(
                        arguments,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )
                    self.assertEqual(result.returncode, expected_returncode, result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["evidence"][0]["source_count"], 1)
                    self.assertEqual(report["evidence"][0]["target_count"], expected_count)

    def test_duplicate_ids_are_input_error(self):
        self.assert_invalid(mapping(item(), item()), "unique")

    def test_invalid_schema_empty_map_and_malformed_items(self):
        values = [
            None,
            [],
            {},
            {"schema_version": True, "items": [item()]},
            {"schema_version": 2, "items": [item()]},
            {"schema_version": 1, "items": []},
            {"schema_version": 1, "items": {}},
            mapping(None),
        ]
        for field in ["id", "source", "target", "kind"]:
            for value in [None, [], "", " "]:
                values.append(mapping(item(**{field: value})))
            incomplete = item()
            del incomplete[field]
            values.append(mapping(incomplete))
        values.append(mapping(item(kind="certified")))
        for value in values:
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_authorized_factual_change_requires_explanation_and_is_visible(self):
        self.assert_invalid(mapping(item(factual_change=True)), "explanation")
        self.assert_invalid(mapping(item(factual_change="yes", explanation="User correction")))
        self.assert_invalid(mapping(item(explanation=[])))
        result = self.check(
            mapping(
                item(
                    source="12 ms",
                    target="20 ms",
                    kind="number",
                    factual_change=True,
                    explanation="User explicitly corrected the measurement to 20 ms.",
                )
            ),
            edited=EDITED.replace("12 ms", "20 ms"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)["evidence"][0]
        self.assertTrue(evidence["factual_change"])
        self.assertIn("User explicitly", evidence["explanation"])

    def test_malformed_deep_json_and_non_json_constants_are_input_errors(self):
        for raw in [
            '{"items":',
            "[" * 2000 + "0" + "]" * 2000,
            '{"schema_version": NaN, "items": []}',
            '{"schema_version":1,"schema_version":1,"items":[]}',
        ]:
            with self.subTest(raw=raw[:80]):
                self.assert_invalid(raw, raw=True)

    def test_invalid_utf8_in_each_input_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("source.txt", "edited.txt", "map.json")]
            for index in range(3):
                for path, text in zip(paths, (SOURCE, EDITED, json.dumps(mapping())), strict=True):
                    path.write_text(text, encoding="utf-8")
                paths[index].write_bytes(b"\xff")
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), *map(str, paths)], capture_output=True, text=True
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("preservation:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(paths[index].read_bytes(), b"\xff")

    def test_missing_input_and_usage_return_two(self):
        for arguments in [[], ["/nonexistent/source", "/nonexistent/edited", "/nonexistent/map"]]:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *arguments], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("can't open file", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_text_output_shows_anchor_counts_and_limits(self):
        result = self.check(mapping(), fmt="text")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("project", result.stdout)
        self.assertIn("source=1 target=1", result.stdout)
        self.assertIn("semantic", result.stdout)

    def test_closed_stdout_returns_two_without_shutdown_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("source.txt", "edited.txt", "map.json")]
            for path, text in zip(paths, (SOURCE, EDITED, json.dumps(mapping())), strict=True):
                path.write_text(text, encoding="utf-8")
            reader, writer = os.pipe()
            os.close(reader)
            try:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), *map(str, paths)],
                    stdout=writer,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            finally:
                os.close(writer)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("preservation:", result.stderr)
            self.assertNotIn("Exception ignored", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_generic_stdout_io_error_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("source.txt", "edited.txt", "map.json")]
            for path, text in zip(paths, (SOURCE, EDITED, json.dumps(mapping())), strict=True):
                path.write_text(text, encoding="utf-8")
            code = (
                "import runpy, sys\n"
                "class FailingWriter:\n"
                " def write(self, text): raise OSError('simulated output failure')\n"
                " def flush(self): pass\n"
                "namespace = runpy.run_path(sys.argv[1])\n"
                "sys.stdout = FailingWriter()\n"
                "raise SystemExit(namespace['main'](sys.argv[2:]))\n"
            )
            result = subprocess.run(
                [sys.executable, "-c", code, str(SCRIPT), *map(str, paths)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("simulated output failure", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_installed_skill_is_self_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / SKILL.name
            shutil.copytree(SKILL, destination)
            result = self.check(mapping(), script=destination / "scripts/check_preservation.py")
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
