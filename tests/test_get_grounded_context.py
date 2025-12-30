from grounded_context_mcp.tools.grounded_context import get_grounded_context


def test_get_grounded_context_reads_files(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world")

    out = get_grounded_context(["a.txt"], root=str(tmp_path))

    assert out["root"] == str(tmp_path)
    assert out["items"][0]["ok"] is True
    assert "hello" in out["items"][0]["content"]


def test_get_grounded_context_missing_file(tmp_path):
    out = get_grounded_context(["missing.txt"], root=str(tmp_path))
    assert out["items"][0]["ok"] is False
