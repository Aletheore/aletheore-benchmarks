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
            raise ValueError("relative executable paths are not allowed; resolve the tool path explicitly")
        else:
            child_env = kwargs.get("env")
            search_path = child_env.get("PATH", os.defpath) if child_env is not None else None
            executable = shutil.which(executable, path=search_path)
            if executable is None:
                raise FileNotFoundError(f"required executable not found on PATH: {command[0]}")
    command[0] = os.path.abspath(executable)
    # The wrapper accepts only argument vectors and explicitly disables shell parsing.
    return subprocess.run(command, shell=False, **kwargs)  # nosec B603
