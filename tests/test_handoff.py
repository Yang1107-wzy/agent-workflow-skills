import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/workflow-repo-handoff/scripts/snapshot.py"


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"], cwd=self.root, check=True
        )
        (self.root / "a.txt").write_text("before")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "fixture"], cwd=self.root, check=True, capture_output=True
        )

    def cli(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_clean_snapshot(self):
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["branch"], "main")
        self.assertFalse(data["changes"])
        self.assertEqual(data["tests"], "not_run_by_snapshot")

    def test_dirty_unicode_paths(self):
        (self.root / "a.txt").write_text("after")
        (self.root / "新资料.txt").write_text("untracked")
        data = json.loads(self.cli().stdout)
        self.assertEqual(len(data["changes"]), 2)
        self.assertIn("新资料.txt", [x["path"] for x in data["changes"]])

    def test_snapshot_does_not_modify_worktree(self):
        before = (self.root / "a.txt").read_bytes()
        self.cli()
        self.assertEqual((self.root / "a.txt").read_bytes(), before)

    def test_missing_repository(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root / "missing")],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_git_paths_decode_under_ascii_locale(self):
        import os

        (self.root / "资料.txt").write_text("text", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("资料.txt", [x["path"] for x in json.loads(r.stdout)["changes"]])
