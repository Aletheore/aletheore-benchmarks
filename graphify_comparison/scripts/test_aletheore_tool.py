import subprocess
from unittest.mock import patch, MagicMock

from aletheore_tool import aletheore_query_tool, set_aletheore_root


def test_aletheore_query_tool_shells_out_with_expected_args():
    set_aletheore_root("/fake/erpnext")
    fake_result = MagicMock(returncode=0, stdout="some output", stderr="")
    with patch("aletheore_tool.subprocess.run", return_value=fake_result) as mock_run:
        out = aletheore_query_tool(kind="search-codebase", target="validate sales invoice")
        args = mock_run.call_args[0][0]
        assert args[:2] == ["aletheore", "query"]
        assert "search-codebase" in args
        assert "--path" in args
        assert "/fake/erpnext" in args
        assert out == "some output"


def test_aletheore_query_tool_reports_a_failing_call_instead_of_raising():
    set_aletheore_root("/fake/erpnext")
    fake_result = MagicMock(returncode=1, stdout="", stderr="bad kind")
    with patch("aletheore_tool.subprocess.run", return_value=fake_result):
        out = aletheore_query_tool(kind="search-codebase", target="something")
        assert "bad kind" in out


def test_aletheore_query_tool_rejects_answer_kind_without_calling_subprocess():
    set_aletheore_root("/fake/erpnext")
    with patch("aletheore_tool.subprocess.run") as mock_run:
        out = aletheore_query_tool(kind="answer")
        assert "error" in out
        assert "answer" in out
        mock_run.assert_not_called()


def test_aletheore_query_tool_catches_timeout_and_returns_error():
    set_aletheore_root("/fake/erpnext")
    with patch("aletheore_tool.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 60)):
        out = aletheore_query_tool(kind="search-codebase", target="something")
        assert "error" in out
        assert isinstance(out, str)
