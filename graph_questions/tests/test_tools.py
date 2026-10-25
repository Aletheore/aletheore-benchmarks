import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _tools import run_tool


class ToolRunnerTests(unittest.TestCase):
    def test_resolves_tool_before_switching_to_repository_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_tool(
                [Path(sys.executable).name, "-c", "import os; print(os.getcwd())"],
                cwd=temporary,
                capture_output=True,
                text=True,
                check=True,
            )
        self.assertEqual(result.stdout.strip(), os.path.realpath(temporary))

    def test_shell_execution_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "shell execution is not supported"):
            run_tool([sys.executable, "-c", "pass"], shell=True)  # nosec B604


if __name__ == "__main__":
    unittest.main()
