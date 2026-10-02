import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "skills/workflow-source-writing/scripts/check_ledger.py"
)


class LedgerTests(unittest.TestCase):
    def check(self, value):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ledger.json"
            p.write_text(json.dumps(value), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(p), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

    def test_supported_requires_observed_evidence(self):
        r = self.check(
            {
                "claims": [
                    {"id": "c1", "claim": "Synthetic claim", "status": "supported", "evidence": []}
                ]
            }
        )
        self.assertEqual(r.returncode, 1)
        self.assertTrue(json.loads(r.stdout)["issues"])

    def test_valid_supported_claim(self):
        r = self.check(
            {
                "claims": [
                    {
                        "id": "c1",
                        "claim": "Synthetic claim",
                        "status": "supported",
                        "evidence": [
                            {
                                "source": "logs/run.txt",
                                "locator": "line 4",
                                "observation": "30 cases",
                                "observed": True,
                            }
                        ],
                    }
                ]
            }
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_unverified_is_allowed_but_visible(self):
        r = self.check(
            {
                "claims": [
                    {"id": "c1", "claim": "Not established", "status": "unverified", "evidence": []}
                ]
            }
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["unverified"], 1)

    def test_unobserved_source_cannot_support(self):
        r = self.check(
            {
                "claims": [
                    {
                        "id": "c1",
                        "claim": "Something",
                        "status": "supported",
                        "evidence": [
                            {
                                "source": "https://example.org",
                                "locator": "page 1",
                                "observation": "not fetched",
                                "observed": False,
                            }
                        ],
                    }
                ]
            }
        )
        self.assertEqual(r.returncode, 1)

    def test_duplicate_ids_and_invalid_status(self):
        r = self.check(
            {
                "claims": [
                    {"id": "x", "claim": "A", "status": "guess", "evidence": []},
                    {"id": "x", "claim": "B", "status": "unverified", "evidence": []},
                ]
            }
        )
        self.assertEqual(r.returncode, 1)
        self.assertGreaterEqual(len(json.loads(r.stdout)["issues"]), 2)

    def test_bad_root_is_findings_not_traceback(self):
        r = self.check([])
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)
