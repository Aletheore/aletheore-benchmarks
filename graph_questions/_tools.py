"""Subprocess boundary for the local benchmark and truth-generation tools."""

import os
import shutil
import subprocess  # nosec B404


def run_tool(argv, **kwargs):
    """Run a known local tool without a shell or PATH shadowing by repo cwd."""
    if not isinstance(argv, (list, tuple)) or not argv or not isinstance(argv[0], str):
        raise TypeError("tool invocation must be a non-empty argument list")
    if kwargs.pop("shell", False):
        raise ValueError("shell execution is not supported")

    command = list(argv)
    executable = command[0]
    if not os.path.isabs(executable):
        if os.sep in executable or (os.altsep and os.altsep in executable):
            working_directory = kwargs.get("cwd") or os.getcwd()
            executable = os.path.abspath(os.path.join(working_directory, executable))
        else:
            executable = shutil.which(executable)
            if executable is None:
                raise FileNotFoundError(f"required executable not found on PATH: {command[0]}")
    command[0] = os.path.abspath(executable)
    # The wrapper accepts only argument vectors and explicitly disables shell parsing.
    return subprocess.run(command, shell=False, **kwargs)  # nosec B603
