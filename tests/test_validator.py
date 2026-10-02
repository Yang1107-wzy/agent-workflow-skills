import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_skills.py"


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skill = self.root / "workflow-example"
        self.skill.mkdir()
        self.write("A complete example skill.")

    def write(self, body, name="workflow-example"):
        (self.skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Use when processing an example fixture.\n---\n\n{body}\n"
        )

    def cli(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(self.root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_valid(self):
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["skills"], 1)

    def test_missing_reference(self):
        self.write("Read [reference](references/missing.md).")
        self.assertEqual(self.cli().returncode, 1)

    def test_external_local_reference_refused(self):
        self.write("Read [outside](../../outside.md).")
        self.assertEqual(self.cli().returncode, 1)

    def test_mismatching_name(self):
        self.write("Complete body.", name="wrong-name")
        self.assertEqual(self.cli().returncode, 1)

    def test_missing_script(self):
        self.write('Run python "<skill-dir>/scripts/missing.py".')
        self.assertEqual(self.cli().returncode, 1)

    def test_unfinished_skill(self):
        self.write("TODO: write the workflow.")
        self.assertEqual(self.cli().returncode, 1)
