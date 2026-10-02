import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/workflow-desktop-triage/scripts/triage.py"


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "Desktop"
        self.source.mkdir()
        (self.source / "资料.txt").write_text("keep original", encoding="utf-8")
        (self.source / "thing.unknown").write_bytes(b"unknown")
        self.dest = self.base / "Classified"

    def cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.source), str(self.dest), *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_preview_never_copies(self):
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.dest.exists())
        self.assertEqual(len(json.loads(r.stdout)["operations"]), 2)

    def test_copy_preserves_originals_and_hashes(self):
        r = self.cli("--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            (self.dest / "notes" / "资料.txt").read_bytes(), (self.source / "资料.txt").read_bytes()
        )
        self.assertEqual((self.dest / "review" / "thing.unknown").read_bytes(), b"unknown")
        self.assertTrue(json.loads(r.stdout)["applied"])

    def test_existing_destination_refused(self):
        self.dest.mkdir()
        (self.dest / "keep").write_text("keep")
        r = self.cli("--apply")
        self.assertEqual(r.returncode, 2)
        self.assertEqual((self.dest / "keep").read_text(), "keep")

    def test_nested_destination_refused(self):
        self.dest = self.source / "Classified"
        self.assertEqual(self.cli("--apply").returncode, 2)
        self.assertFalse(self.dest.exists())

    def test_same_basename_in_subfolders_preserved(self):
        for name in ["a", "b"]:
            (self.source / name).mkdir()
            (self.source / name / "note.txt").write_text(name)
        r = self.cli("--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dest / "notes/a/note.txt").read_text(), "a")
        self.assertEqual((self.dest / "notes/b/note.txt").read_text(), "b")
