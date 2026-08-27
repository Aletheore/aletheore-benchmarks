import os
import tempfile

from baseline_tools import grep_tool, read_file_tool, list_dir_tool, set_root


def test_grep_tool_finds_a_real_match():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "a.py"), "w") as f:
            f.write("def validate_sales_invoice():\n    pass\n")
        set_root(tmp)
        out = grep_tool("validate_sales_invoice")
        assert "a.py" in out
        assert "validate_sales_invoice" in out


def test_read_file_tool_reads_a_line_range():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "b.py"), "w") as f:
            f.write("line1\nline2\nline3\n")
        set_root(tmp)
        out = read_file_tool("b.py", start_line=2, end_line=2)
        assert out.strip() == "line2"


def test_list_dir_tool_lists_real_entries():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "sub"))
        open(os.path.join(tmp, "file.txt"), "w").close()
        set_root(tmp)
        out = list_dir_tool(".")
        assert "sub" in out
        assert "file.txt" in out
