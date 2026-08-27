import subprocess
from unittest.mock import patch, MagicMock

from graphify_tool import graphify_query_tool, set_graphify_root


def test_graphify_query_mode_shells_out_correctly():
    set_graphify_root("/fake/erpnext")
    fake_result = MagicMock(returncode=0, stdout="graph answer", stderr="")
    with patch("graphify_tool.subprocess.run", return_value=fake_result) as mock_run:
        out = graphify_query_tool(mode="query", query="what connects X to Y?")
        args = mock_run.call_args[0][0]
        assert args[:2] == ["graphify", "query"]
        assert "what connects X to Y?" in args
        assert mock_run.call_args[1]["cwd"] == "/fake/erpnext"
        assert out == "graph answer"


def test_graphify_path_mode_passes_both_endpoints():
    set_graphify_root("/fake/erpnext")
    fake_result = MagicMock(returncode=0, stdout="path found", stderr="")
    with patch("graphify_tool.subprocess.run", return_value=fake_result) as mock_run:
        graphify_query_tool(mode="path", a="auth.py", b="database.py")
        args = mock_run.call_args[0][0]
        assert args[:2] == ["graphify", "path"]
        assert "auth.py" in args and "database.py" in args


def test_graphify_query_tool_rejects_invalid_mode():
    set_graphify_root("/fake/erpnext")
    with patch("graphify_tool.subprocess.run") as mock_run:
        out = graphify_query_tool(mode="invalid")
        assert "error" in out
        assert "invalid" in out
        mock_run.assert_not_called()


def test_graphify_query_tool_reports_failing_call_instead_of_raising():
    set_graphify_root("/fake/erpnext")
    fake_result = MagicMock(returncode=1, stdout="", stderr="command failed")
    with patch("graphify_tool.subprocess.run", return_value=fake_result):
        out = graphify_query_tool(mode="query", query="test")
        assert "error" in out
        assert "command failed" in out


def test_graphify_query_tool_catches_timeout_and_returns_error():
    set_graphify_root("/fake/erpnext")
    with patch("graphify_tool.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
        out = graphify_query_tool(mode="query", query="test")
        assert "error" in out
        assert isinstance(out, str)
