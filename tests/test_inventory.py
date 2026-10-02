import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/workflow-materials-intake/scripts/inventory.py"


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "资料.txt").write_text("synthetic text", encoding="utf-8")
        (self.root / "copy.txt").write_text("synthetic text", encoding="utf-8")
        (self.root / "draft.md").write_text("not approved")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_hash_duplicates_and_unicode(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(len(data["files"]), 3)
        self.assertEqual(len(data["duplicates"]), 1)
        self.assertEqual(data["duplicates"][0]["paths"], ["copy.txt", "资料.txt"])

    def test_ignores_hidden_and_app_packages(self):
        (self.root / ".env").write_text("synthetic only")
        app = self.root / "Demo.app"
        app.mkdir()
        (app / "secret.txt").write_text("skip")
        data = json.loads(self.run_cli().stdout)
        self.assertEqual(len(data["files"]), 3)
        self.assertTrue(data["skipped"])

    def test_symlink_excluded(self):
        target = self.root / "资料.txt"
        link = self.root / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        data = json.loads(self.run_cli().stdout)
        self.assertNotIn("link.txt", [x["path"] for x in data["files"]])

    def test_file_limit_fails_without_partial_report(self):
        r = self.run_cli("--max-files", "1")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(r.stdout)

    def test_markdown(self):
        r = self.run_cli("--format", "markdown")
        self.assertEqual(r.returncode, 0)
        self.assertIn("sha256", r.stdout.lower())
        self.assertIn("资料.txt", r.stdout)

    def test_missing_root(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root / "absent")],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_source_is_untouched(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.run_cli()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_incomplete_downloads_skipped(self):
        (self.root / "active.crdownload").write_text("partial")
        data = json.loads(self.run_cli().stdout)
        self.assertIn("active.crdownload", data["skipped"])

    def test_selected_application_package_refused(self):
        package = self.root / "Demo.app"
        package.mkdir()
        (package / "a.txt").write_text("package content")
        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(package)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(r.returncode, 2)

    def test_markdown_output_uses_utf8_under_legacy_console(self):
        import os

        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root), "--format", "markdown"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("资料.txt", r.stdout)
