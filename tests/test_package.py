import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package.py"


class PackageTests(unittest.TestCase):
    def test_bundle_self_contained_without_private_logs_or_caches(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "skills.zip"
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(target), "--version", "0.1.0"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            with zipfile.ZipFile(target) as z:
                names = z.namelist()
                expected = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
                included = {Path(n).parent.name for n in names if n.endswith("/SKILL.md")}
                self.assertEqual(included, expected)
                self.assertFalse(
                    any(
                        "__pycache__" in n or "forward-evals" in n or "/baseline/" in n
                        for n in names
                    )
                )
                self.assertTrue(any(n.endswith("/scripts/install.py") for n in names))

    def test_existing_archive_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "skills.zip"
            target.write_bytes(b"keep")
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(r.returncode, 2)
            self.assertEqual(target.read_bytes(), b"keep")

    def test_raced_in_archive_is_not_deleted(self):
        from unittest import mock

        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import package as module
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "skills.zip"
            original = Path.open

            def race(path, mode="r", *args, **kwargs):
                if path == target and mode == "xb":
                    with original(path, "wb") as f:
                        f.write(b"raced-in-file")
                    raise FileExistsError("synthetic race")
                return original(path, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", race), self.assertRaises(FileExistsError):
                module.package(target, "0.1.0")
            self.assertEqual(target.read_bytes(), b"raced-in-file")
