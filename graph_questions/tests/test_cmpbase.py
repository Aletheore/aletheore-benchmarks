import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

GRAPH_QUESTIONS = Path(__file__).resolve().parents[1]
CMPBASE = GRAPH_QUESTIONS / "truth/scripts/truth_work_jvmnet/cmpbase.py"


class LegacyComparisonTests(unittest.TestCase):
    def run_cmpbase(self, source):
        with tempfile.TemporaryDirectory() as temporary:
            legacy = Path(temporary) / "legacy.py"
            legacy.write_text(source, encoding="utf-8")
            env = os.environ.copy()
            env["TRUTH_REGEX_SOURCE"] = str(legacy)
            return subprocess.run(
                [sys.executable, str(CMPBASE)],
                cwd=GRAPH_QUESTIONS,
                env=env,
                capture_output=True,
                text=True,
            )

    def test_duplicate_base_assignments_are_rejected_before_import(self):
        result = self.run_cmpbase('L = "first"\nL = "second"\nraise RuntimeError("must not run")\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one top-level `L = ...` assignment", result.stderr)
        self.assertNotIn("must not run", result.stderr)

    def test_explicit_module_import_applies_repository_root(self):
        result = self.run_cmpbase(
            'L = "/wrong"\n'
            'def java_graph(repo):\n    assert L == "./"\n    return [L], {}\n'
            'def cs_graph(repo):\n    assert L == "./"\n    return [L], {}, None\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
