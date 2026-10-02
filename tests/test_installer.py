import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/install.py"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(self.home), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_default_is_preview(self):
        r = self.cli("--target", "both", "--skill", "workflow-materials-intake")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.home / ".agents").exists())
        self.assertEqual(len(json.loads(r.stdout)["destinations"]), 2)

    def test_user_install_both(self):
        r = self.cli("--target", "both", "--skill", "workflow-materials-intake", "--apply")
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in [".agents", ".claude"]:
            self.assertTrue(
                (self.home / name / "skills/workflow-materials-intake/SKILL.md").is_file()
            )
            self.assertTrue(
                (
                    self.home / name / "skills/workflow-materials-intake/scripts/inventory.py"
                ).is_file()
            )

    def test_existing_skill_preserved(self):
        target = self.home / ".agents/skills/workflow-materials-intake"
        target.mkdir(parents=True)
        (target / "keep.txt").write_text("keep")
        self.assertEqual(
            self.cli(
                "--target", "both", "--skill", "workflow-materials-intake", "--apply"
            ).returncode,
            2,
        )
        self.assertEqual((target / "keep.txt").read_text(), "keep")
        self.assertFalse((self.home / ".claude/skills/workflow-materials-intake").exists())

    def test_project_install(self):
        r = self.cli(
            "--target",
            "codex",
            "--scope",
            "project",
            "--project-root",
            str(self.home),
            "--skill",
            "workflow-materials-intake",
            "--apply",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.home / ".agents/skills/workflow-materials-intake/SKILL.md").is_file())

    def test_unknown_skill_refused(self):
        self.assertEqual(self.cli("--skill", "../../outside", "--apply").returncode, 2)

    def test_destination_cannot_be_inside_source_skill(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("workflow_installer", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bundle = self.home / "bundle"
        source = bundle / "example"
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text("synthetic")
        module.BUNDLE = bundle
        with self.assertRaises(ValueError):
            module.install(scope="project", project_root=source, selected=["example"], apply=False)
        self.assertFalse((source / ".agents").exists())
