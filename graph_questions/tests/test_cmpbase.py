import os
import json
from pathlib import Path
import sys
import tempfile
import unittest

GRAPH_QUESTIONS = Path(__file__).resolve().parents[1]
CMPBASE = GRAPH_QUESTIONS / "truth/scripts/truth_work_jvmnet/cmpbase.py"
sys.path.insert(0, str(GRAPH_QUESTIONS))
from _tools import run_tool


class LegacyComparisonTests(unittest.TestCase):
    def run_cmpbase(self, source):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy.py"
            legacy.write_text(source, encoding="utf-8")
            truth = root / "truth"
            truth.mkdir()
            for repo in ("gson", "thrift", "automapper"):
                (truth / f"{repo}.json").write_text(json.dumps({"edges": [], "files": []}), encoding="utf-8")
            env = os.environ.copy()
            env["TRUTH_REGEX_SOURCE"] = str(legacy)
            return run_tool(
                [sys.executable, str(CMPBASE)], cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

    def test_duplicate_base_assignments_are_rejected_before_import(self):
        result = self.run_cmpbase('L = "first"\nL = "second"\nraise RuntimeError("must not run")\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one top-level `L = ...` assignment", result.stderr)
        self.assertNotIn("must not run", result.stderr)

    def test_explicit_module_import_applies_repository_root(self):
        result = self.run_cmpbase(
            'L = "/wrong"\nROOT_AT_IMPORT = L\n'
            'def java_graph(repo):\n    assert ROOT_AT_IMPORT == "./"\n    return [], {}\n'
            'def cs_graph(repo):\n    assert ROOT_AT_IMPORT == "./"\n    return [], {}, None\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_comparison_expression_is_not_counted_as_base_assignment(self):
        result = self.run_cmpbase(
            'L = "/wrong"\n'
            'if L == "/wrong":\n    pass\n'
            'def java_graph(repo): return [], {}\n'
            'def cs_graph(repo): return [], {}, None\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_augmented_assignment_is_not_counted_as_simple_base_assignment(self):
        result = self.run_cmpbase(
            'L += "/extra"\n'
            'def java_graph(repo): return [], {}\n'
            'def cs_graph(repo): return [], {}, None\n'
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one top-level `L = ...` assignment", result.stderr)


if __name__ == "__main__":
    unittest.main()
