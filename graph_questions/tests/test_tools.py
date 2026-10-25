import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
GRAPH_QUESTIONS = Path(__file__).resolve().parents[1]

from _tools import run_tool


class ToolRunnerTests(unittest.TestCase):
    def test_resolves_tool_before_switching_to_repository_directory(self):
        if os.name == "nt":
            self.skipTest("POSIX executable fixture")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trusted_bin = root / "trusted-bin"
            hostile_repo = root / "repository"
            trusted_bin.mkdir()
            hostile_repo.mkdir()
            for folder, output in ((trusted_bin, "trusted"), (hostile_repo, "hostile")):
                executable = folder / "probe-tool"
                executable.write_text(f"#!/bin/sh\nprintf '%s' {output}\n", encoding="utf-8")
                executable.chmod(0o755)
            result = run_tool(
                ["probe-tool"], cwd=hostile_repo, env={"PATH": str(trusted_bin)},
                capture_output=True, text=True, check=True,
            )
        self.assertEqual(result.stdout, "trusted")

    def test_relative_executable_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "relative executable paths are not allowed"):
            run_tool(["./tool"])

    def test_standalone_scripts_import_shared_tool_from_outside_checkout(self):
        scripts = (
            GRAPH_QUESTIONS / "ml_pick.py",
            GRAPH_QUESTIONS / "truth/scripts/make_refs_python.py",
            GRAPH_QUESTIONS / "truth/scripts/make_truth_js.py",
        )
        with tempfile.TemporaryDirectory() as temporary:
            for script in scripts:
                with self.subTest(script=script.name):
                    result = run_tool(
                        [sys.executable, str(script)], cwd=temporary,
                        capture_output=True, text=True, encoding="utf-8",
                    )
                    self.assertNotIn("No module named '_tools'", result.stderr)

    def test_shell_execution_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "shell execution is not supported"):
            run_tool([sys.executable, "-c", "pass"], shell=True)  # nosec B604


if __name__ == "__main__":
    unittest.main()
