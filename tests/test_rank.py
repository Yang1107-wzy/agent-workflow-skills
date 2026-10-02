import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/workflow-skill-research/scripts/rank_candidates.py"
)


class RankTests(unittest.TestCase):
    def row(self, name="example", **changes):
        return dict(
            name=name,
            utility=4,
            portability=5,
            evidence=3,
            complexity=2,
            maintenance=2,
            overlaps_existing=False,
            sources=[
                {"url": "https://example.org", "access": "indexed", "checked_on": "2026-10-02"}
            ],
            **changes,
        )

    def cli(self, rows):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps({"candidates": rows}))
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(p)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

    def test_scores_and_order(self):
        a = self.row("useful")
        b = self.row("complex")
        b["complexity"] = 5
        r = self.cli([b, a])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["ranked"][0]["name"], "useful")

    def test_overlap_penalty(self):
        a = self.row("original")
        b = self.row("duplicate")
        b["overlaps_existing"] = True
        data = json.loads(self.cli([a, b]).stdout)
        self.assertEqual(data["ranked"][0]["score"] - data["ranked"][1]["score"], 5)

    def test_invalid_score_bool_refused(self):
        row = self.row()
        row["utility"] = True
        self.assertEqual(self.cli([row]).returncode, 2)

    def test_missing_sources_refused(self):
        row = self.row()
        row["sources"] = []
        self.assertEqual(self.cli([row]).returncode, 2)

    def test_bad_date_refused(self):
        row = self.row()
        row["sources"][0]["checked_on"] = "yesterday"
        self.assertEqual(self.cli([row]).returncode, 2)

    def test_duplicate_names_refused(self):
        self.assertEqual(self.cli([self.row(), self.row()]).returncode, 2)
